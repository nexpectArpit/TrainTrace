"""Durable admission and scheduling shared by training and scientific audits."""

import json
from uuid import uuid4
from db.database import database
from config import ARTIFACTS_DIR
from storage import sha256, resolve_managed_path
from snapshot_contracts import decode_config, decode_snapshot


def submit_run(config):
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        payload = config.model_dump()
        queue_policy = payload.pop("queue_policy", "queue")
        if (
            queue_policy == "reject"
            and c.execute(
                "SELECT 1 FROM jobs WHERE status IN ('QUEUED','RUNNING') LIMIT 1"
            ).fetchone()
        ):
            raise ValueError(
                "Another job is active; this run was rejected by the selected queue policy."
            )
        exp = c.execute("SELECT * FROM experiments WHERE id=?", (config.experiment_id,)).fetchone()
        if not exp or exp["archived"]:
            raise ValueError("Choose an existing, active investigation.")
        if c.execute("SELECT 1 FROM runs WHERE id=?", (config.run_id,)).fetchone():
            raise ValueError("Run ID already exists. Use a new ID.")
        if config.predecessor_run_id:
            parent = c.execute(
                "SELECT * FROM runs WHERE id=?", (config.predecessor_run_id,)
            ).fetchone()
            if not parent or parent["experiment_id"] != config.experiment_id:
                raise ValueError("Predecessor must belong to this investigation.")
            decision = c.execute(
                "SELECT * FROM decisions WHERE run_id=? ORDER BY id DESC LIMIT 1", (parent["id"],)
            ).fetchone()
            if not decision:
                raise ValueError("Record the predecessor limitations before branching.")
        if config.initialize_from_run_id:
            source = c.execute(
                "SELECT * FROM runs WHERE id=? AND experiment_id=?",
                (config.initialize_from_run_id, config.experiment_id),
            ).fetchone()
            if not source or source["status"] not in ("COMPLETED", "STOPPED", "FAILED"):
                raise ValueError("Warm-start source must be a finished run in this investigation")
            source_config = decode_config(source["config_json"]) or {}
            source_dataset = decode_snapshot(source["dataset_json"], "dataset") or {}
            from core.dataset import dataset_spec

            _, target_spec = dataset_spec(config.dataset_name)
            if (
                source_config.get("model_name") != config.model_name
                or bool(source_config.get("pretrained")) != bool(config.pretrained)
                or source_config.get("architecture_config", {})
                != payload.get("architecture_config", {})
                or source_dataset.get("num_classes") != target_spec["num_classes"]
            ):
                raise ValueError("Warm-start source architecture and output classes must match")
            checkpoint = c.execute(
                "SELECT path,sha256,kind FROM artifacts WHERE run_id=? AND kind IN ('best_checkpoint','last_checkpoint') "
                "ORDER BY CASE kind WHEN 'best_checkpoint' THEN 0 ELSE 1 END LIMIT 1",
                (config.initialize_from_run_id,),
            ).fetchone()
            if not checkpoint:
                raise ValueError("Warm-start source has no saved checkpoint")
            checkpoint_path = resolve_managed_path(ARTIFACTS_DIR, checkpoint["path"])
            if not checkpoint_path.is_file() or sha256(checkpoint_path) != checkpoint["sha256"]:
                raise ValueError(
                    "Warm-start checkpoint is missing or failed integrity verification"
                )
            payload["warm_start_checkpoint_sha256"] = checkpoint["sha256"]
            payload["warm_start_checkpoint_kind"] = checkpoint["kind"]
        payload["config_schema_version"] = 1
        execution_target = payload.get("execution_target", "local")
        if execution_target == "kaggle":
            if config.initialize_from_run_id:
                raise ValueError(
                    "Kaggle runs cannot warm-start from a local checkpoint yet. "
                    "Choose execution target Local, or start this Kaggle run from fresh initialization."
                )
            from cloud.credentials import get_kaggle_credentials, resolve_kaggle_username

            creds = get_kaggle_credentials()
            if not creds["configured"]:
                raise ValueError(
                    "Kaggle Cloud GPU execution requires credentials. "
                    "Paste your KAGGLE_USERNAME and KAGGLE_KEY into traintrace/.env "
                    "or place kaggle.json in ~/.kaggle/."
                )
            try:
                username = resolve_kaggle_username(force=True)
            except Exception as exc:
                raise ValueError(f"Kaggle credentials could not be verified: {exc}") from exc
            job_kind = "kaggle_train"
            queue_message = f"Queued for Kaggle Cloud GPU execution (user: @{username})."
        else:
            job_kind = "train"
            queue_message = "Queued for the single local worker."

        insert_run(c, payload)
        c.execute(
            "INSERT INTO jobs(id,kind,payload) VALUES(?,?,?)",
            (config.run_id, job_kind, json.dumps(payload)),
        )
    return {
        "job_id": config.run_id,
        "run_id": config.run_id,
        "status": "QUEUED",
        "message": queue_message,
    }


def submit_final_evaluation(request):
    """Reserve the one-time final test evaluation for a selected candidate."""
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        run = c.execute("SELECT * FROM runs WHERE id=?", (request.run_id,)).fetchone()
        if not run:
            raise ValueError("Run not found")
        if run["status"] != "COMPLETED" or not run["validation_json"]:
            raise ValueError("A completed run with validation evidence is required")
        validation = decode_snapshot(run["validation_json"], "validation")
        if not validation.get("checkpoint_sha256"):
            raise ValueError(
                "This legacy run has no checkpoint integrity snapshot; retrain it before final evaluation"
            )
        decision = c.execute(
            "SELECT status FROM decisions WHERE run_id=? ORDER BY id DESC LIMIT 1",
            (request.run_id,),
        ).fetchone()
        if not decision or decision["status"] != "SELECTED":
            raise ValueError("Select this candidate before final test evaluation")
        if run["final_evaluation_status"] != "NOT_STARTED":
            raise ValueError(
                f"Final test evaluation has already been reserved ({run['final_evaluation_status']})."
            )
        experiment = c.execute(
            "SELECT final_evaluation_run_id FROM experiments WHERE id=?",
            (run["experiment_id"],),
        ).fetchone()
        if experiment["final_evaluation_run_id"] not in (None, request.run_id):
            raise ValueError("This investigation has already used its one final test evaluation")
        claimed = c.execute(
            "UPDATE experiments SET final_evaluation_run_id=? "
            "WHERE id=? AND (final_evaluation_run_id IS NULL OR final_evaluation_run_id=?)",
            (request.run_id, run["experiment_id"], request.run_id),
        ).rowcount
        if not claimed:
            raise ValueError("This investigation has already used its one final test evaluation")
        job_id = "final_" + uuid4().hex
        c.execute(
            "INSERT INTO jobs(id,kind,payload) VALUES(?,?,?)",
            (job_id, "final_evaluation", json.dumps({"run_id": request.run_id})),
        )
        c.execute(
            "UPDATE runs SET final_evaluation_status='QUEUED',final_evaluation_job_id=? WHERE id=?",
            (job_id, request.run_id),
        )
    return {"job_id": job_id, "run_id": request.run_id, "status": "QUEUED"}


def insert_run(c, payload, audit_id=None):
    c.execute(
        """INSERT INTO runs(id,experiment_id,approach_name,model_architecture,batch_size,epochs,learning_rate,seed,
                 config_json,predecessor_run_id,motivating_reason,audit_id,tags_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            payload["run_id"],
            payload["experiment_id"],
            payload["approach_name"],
            payload["model_name"],
            payload["batch_size"],
            payload["epochs"],
            payload["learning_rate"],
            payload["seed"],
            json.dumps(payload),
            payload.get("predecessor_run_id"),
            payload.get("motivating_reason", ""),
            audit_id,
            json.dumps(payload.get("tags", {})),
        ),
    )


def submit_audit(request, protocol):
    with database() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (request.run_id,)).fetchone()
        if (
            not row
            or row["status"] != "COMPLETED"
            or not row["config_json"]
            or not row["validation_json"]
        ):
            raise ValueError(
                "Audit requires a completed run with captured configuration and validation evidence."
            )
        job_id = "audit_" + uuid4().hex
        payload = {"run_id": request.run_id, "protocol": protocol, "seeds": request.seeds}
        c.execute(
            "INSERT INTO jobs(id,kind,payload) VALUES(?,?,?)",
            (job_id, "audit", json.dumps(payload)),
        )
        c.execute(
            "INSERT INTO audits(id,run_id,protocol) VALUES(?,?,?)",
            (job_id, request.run_id, protocol),
        )
    return {"job_id": job_id, "status": "QUEUED"}


def stop_job(job_id):
    remote_kernel_id = None
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        job = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise ValueError("Job not found")
        if job["status"] not in ["QUEUED", "RUNNING"]:
            raise ValueError("Job is already finished")
        if (
            job["kind"] in ("train", "kaggle_train", "final_evaluation")
            and job["status"] == "RUNNING"
        ):
            run = c.execute(
                "SELECT status,final_evaluation_status FROM runs WHERE id=? OR final_evaluation_job_id=?",
                (job_id, job_id),
            ).fetchone()
            if run and (
                (
                    job["kind"] in ("train", "kaggle_train")
                    and run["status"] in ("COMPLETED", "FAILED", "STOPPED")
                )
                or (
                    job["kind"] == "final_evaluation"
                    and run["final_evaluation_status"] in ("COMPLETED", "FAILED", "STOPPED")
                )
            ):
                raise ValueError("The job finished before the stop request was applied")
        if job["status"] == "QUEUED":
            changed = c.execute(
                "UPDATE jobs SET status='STOPPED',cancel_requested=1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='QUEUED'",
                (job_id,),
            ).rowcount
            if not changed:
                raise ValueError("Job changed state before the stop request was applied")
            if job["kind"] in ("train", "kaggle_train"):
                c.execute("UPDATE runs SET status='STOPPED' WHERE id=?", (job_id,))
            elif job["kind"] == "final_evaluation":
                c.execute(
                    "UPDATE runs SET final_evaluation_status='STOPPED' WHERE final_evaluation_job_id=?",
                    (job_id,),
                )
        else:
            changed = c.execute(
                "UPDATE jobs SET cancel_requested=1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='RUNNING'",
                (job_id,),
            ).rowcount
            if not changed:
                raise ValueError("Job completed before the stop request was applied")
            if job["kind"] == "kaggle_train":
                run = c.execute("SELECT progress_json FROM runs WHERE id=?", (job_id,)).fetchone()
                if run and run["progress_json"]:
                    try:
                        remote_kernel_id = json.loads(run["progress_json"]).get("kernel_id")
                    except (TypeError, json.JSONDecodeError):
                        pass
                if not remote_kernel_id:
                    event = c.execute(
                        "SELECT message FROM events WHERE run_id=? AND message LIKE 'Kaggle kernel pushed successfully. Kernel ID:%' ORDER BY id DESC LIMIT 1",
                        (job_id,),
                    ).fetchone()
                    if event:
                        remote_kernel_id = event["message"].split("Kernel ID:", 1)[-1].strip()
    message = "Stop requested; completed epochs and checkpoints are retained."
    if job["kind"] == "kaggle_train":
        message += " TrainTrace cannot stop the Kaggle kernel through the installed Kaggle API; stop the remote session on Kaggle."
        if remote_kernel_id:
            message += f" Kernel: {remote_kernel_id}."
        else:
            message += " The kernel ID is not yet available; check Kaggle if submission completes."
    return {"message": message}
