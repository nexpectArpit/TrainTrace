"""Durable admission and scheduling shared by training and scientific audits."""

import json
from uuid import uuid4
from db.database import database


def submit_run(config):
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
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
        payload = config.model_dump()
        insert_run(c, payload)
        c.execute(
            "INSERT INTO jobs(id,kind,payload) VALUES(?,?,?)",
            (config.run_id, "train", json.dumps(payload)),
        )
    return {
        "job_id": config.run_id,
        "run_id": config.run_id,
        "status": "QUEUED",
        "message": "Queued for the single local worker.",
    }


def insert_run(c, payload, audit_id=None):
    c.execute(
        """INSERT INTO runs(id,experiment_id,approach_name,model_architecture,batch_size,epochs,learning_rate,seed,
                 config_json,predecessor_run_id,motivating_reason,audit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
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
        ),
    )


def submit_audit(request, protocol):
    with database() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (request.run_id,)).fetchone()
        if (
            not row
            or row["status"] != "COMPLETED"
            or not row["config_json"]
            or not row["evaluation_json"]
        ):
            raise ValueError(
                "Audit requires a completed run with captured configuration and holdout evaluation. Re-run legacy candidates first."
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
    with database() as c:
        job = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise ValueError("Job not found")
        if job["status"] not in ["QUEUED", "RUNNING"]:
            raise ValueError("Job is already finished")
        c.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (job_id,))
        if job["status"] == "QUEUED":
            c.execute(
                "UPDATE jobs SET status='STOPPED',updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (job_id,),
            )
            if job["kind"] == "train":
                c.execute("UPDATE runs SET status='STOPPED' WHERE id=?", (job_id,))
    return {"message": "Stop requested; completed epochs and checkpoints are retained."}
