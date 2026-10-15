"""One local process owns all training and audits; SQLite queue survives restarts."""

import fcntl
import os
import json
import signal
import time
import traceback
from config import STORAGE_DIR
from db.database import database, init_db


def recover():
    with database() as c:
        c.execute(
            "UPDATE jobs SET status='FAILED',error='Worker interrupted; submit a new run or audit.',updated_at=CURRENT_TIMESTAMP WHERE status='RUNNING'"
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
        return dict(row) if row else None


def work(job):
    from core.trainer import TrainingStopped

    try:
        payload = json.loads(job["payload"])
        if job["kind"] == "train":
            from tracking.tracker import execute_run

            execute_run(payload, job["id"])
        else:
            from tracking.evaluator import execute_audit

            execute_audit(payload, job["id"])
        status, error = "COMPLETED", None
    except TrainingStopped as e:
        status, error = "STOPPED", str(e)
    except Exception:
        status, error = "FAILED", traceback.format_exc()
    with database() as c:
        c.execute(
            "UPDATE jobs SET status=?,error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error, job["id"]),
        )


def main():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with (STORAGE_DIR / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
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
                work(job)
            else:
                time.sleep(0.25)


if __name__ == "__main__":
    main()
