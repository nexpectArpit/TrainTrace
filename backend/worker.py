"""One local process owns all training and audits; SQLite queue survives restarts."""

import os
import json
import signal
import time
import traceback
import multiprocessing
from config import STORAGE_DIR
from db.database import database, init_db
from process_lock import try_lock, unlock


def recover():
    with database() as c:
        c.execute(
            "UPDATE jobs SET status='FAILED',error='Worker interrupted; submit a new run or audit.',updated_at=CURRENT_TIMESTAMP WHERE status='RUNNING'"
        )
        c.execute(
            "UPDATE runs SET final_evaluation_status='FAILED',"
            "final_evaluation_error='Worker stopped during the reserved final evaluation.' "
            "WHERE final_evaluation_status='RUNNING'"
        )
        c.execute(
            "UPDATE runs SET status='FAILED',error='Execution interrupted before durable completion; recorded epochs/artifacts retained.' WHERE status IN ('RUNNING','EVALUATING')"
        )
        c.execute(
            "UPDATE runs SET status='FAILED',error='Audit interrupted before this replay started.' WHERE status='QUEUED' AND audit_id IN (SELECT id FROM jobs WHERE status IN ('FAILED','STOPPED'))"
        )
        # A legacy QUEUED record has no job; do not pretend it can resume.
        c.execute(
            "UPDATE runs SET status='FAILED',error='Legacy queued record has no executable job.' WHERE status='QUEUED' AND audit_id IS NULL AND id NOT IN (SELECT id FROM jobs WHERE status='QUEUED')"
        )


def claim():
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        if c.execute("SELECT 1 FROM jobs WHERE status='RUNNING'").fetchone():
            return None
        row = c.execute(
            "SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created_at,rowid LIMIT 1"
        ).fetchone()
        if row:
            c.execute(
                "UPDATE jobs SET status='RUNNING',updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (row["id"],),
            )
            if row["kind"] == "final_evaluation":
                c.execute(
                    "UPDATE runs SET final_evaluation_status='RUNNING' "
                    "WHERE final_evaluation_job_id=? AND final_evaluation_status='QUEUED'",
                    (row["id"],),
                )
        return dict(row) if row else None


def work(job):
    import torch

    # Job subprocesses may load newer tracking code than a long-lived API process.
    # Apply pending additive migrations before the first training batch writes data.
    init_db()
    torch.set_num_threads(int(os.getenv("TRAINTRACE_CPU_THREADS", "4")))
    from core.trainer import TrainingStopped

    try:
        payload = json.loads(job["payload"])
        if job["kind"] == "train":
            from tracking.tracker import execute_run

            execute_run(payload, job["id"])
        elif job["kind"] == "kaggle_train":
            from cloud.kaggle_bridge import execute_remote_kaggle_run

            def check_cancel():
                with database() as c:
                    row = c.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job["id"],)).fetchone()
                    return bool(row and row["cancel_requested"])

            execute_remote_kaggle_run(payload, job["id"], check_cancelled=check_cancel)
        elif job["kind"] == "audit":
            from tracking.evaluator import execute_audit

            execute_audit(payload, job["id"])
        elif job["kind"] == "final_evaluation":
            from tracking.evaluator import execute_final_evaluation

            execute_final_evaluation(payload, job["id"])
        else:
            raise ValueError(f"Unsupported job kind: {job['kind']}")
        status, error = "COMPLETED", None
    except TrainingStopped as e:
        status, error = "STOPPED", str(e)
    except Exception:
        status, error = "FAILED", traceback.format_exc()
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        current = c.execute(
            "SELECT status,cancel_requested FROM jobs WHERE id=?", (job["id"],)
        ).fetchone()
        if current and current["status"] == "RUNNING" and current["cancel_requested"] and status == "COMPLETED":
            status, error = "STOPPED", "Stop requested before the job result was committed."
            if job["kind"] in ("train", "kaggle_train"):
                c.execute(
                    "UPDATE runs SET status='STOPPED',error=? WHERE id=? AND status='COMPLETED'",
                    (error, job["id"]),
                )
        if job["kind"] == "final_evaluation":
            final_status = "STOPPED" if status == "STOPPED" else "FAILED" if status == "FAILED" else "COMPLETED"
            c.execute(
                "UPDATE runs SET final_evaluation_status=?,final_evaluation_error=? "
                "WHERE final_evaluation_job_id=?",
                (final_status, error, job["id"]),
            )
        elif job["kind"] in ("train", "kaggle_train"):
            c.execute(
                "UPDATE runs SET status=?,error=? WHERE id=? AND status IN ('QUEUED','RUNNING','EVALUATING')",
                (status, error, job["id"]),
            )
        c.execute(
            "UPDATE jobs SET status=?,error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error, job["id"]),
        )


def supervise(job):
    """Give cooperative cancellation five seconds, then stop the isolated job."""
    child = multiprocessing.get_context("spawn").Process(target=work, args=(job,))
    child.start()
    stop_started = None
    try:
        while child.is_alive():
            (STORAGE_DIR / "worker.heartbeat").write_text(str(time.time()))
            with database() as c:
                row = c.execute("SELECT status,cancel_requested FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if row and row["status"] == "RUNNING" and row["cancel_requested"]:
                if stop_started is None:
                    stop_started = time.monotonic()
                if time.monotonic() - stop_started >= 5:
                    child.terminate()
                    child.join(timeout=3)
                    if child.is_alive():
                        child.kill()
                        child.join()
                    break
            child.join(timeout=0.25)
        child.join()
        with database() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT status,cancel_requested FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if row and row["status"] == "RUNNING":
                status = "STOPPED" if row["cancel_requested"] else "FAILED"
                error = "Stopped by user; completed epochs and committed checkpoints retained." if status == "STOPPED" else f"Job process exited unexpectedly (exit code {child.exitcode})."
                c.execute("UPDATE jobs SET status=?,error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, error, job["id"]))
                if job["kind"] in ("train", "kaggle_train"):
                    c.execute("UPDATE runs SET status=?,error=? WHERE id=?", (status, error, job["id"]))
                elif job["kind"] == "final_evaluation":
                    c.execute("UPDATE runs SET final_evaluation_status=?,final_evaluation_error=? WHERE final_evaluation_job_id=?", (status, error, job["id"]))
                elif job["kind"] == "audit":
                    c.execute("UPDATE runs SET status=?,error=? WHERE audit_id=? AND status IN ('QUEUED','RUNNING','EVALUATING')", (status, error, job["id"]))
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=3)
            if child.is_alive():
                child.kill()
                child.join()


def main():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with (STORAGE_DIR / "worker.lock").open("a+b") as lock:
        if not try_lock(lock):
            return
        try:
            import torch

            torch.set_num_threads(int(os.getenv("TRAINTRACE_CPU_THREADS", "4")))
            init_db()
            recover()
            running = True

            def stop(*_):
                nonlocal running
                running = False
                with database() as c:
                    c.execute("UPDATE jobs SET cancel_requested=1 WHERE status='RUNNING'")

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            while running:
                (STORAGE_DIR / "worker.heartbeat").write_text(str(time.time()))
                job = claim()
                if job:
                    supervise(job)
                else:
                    time.sleep(0.25)
        finally:
            unlock(lock)


if __name__ == "__main__":
    main()
