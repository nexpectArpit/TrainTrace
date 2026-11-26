"""Decision transactions and frozen evidence assembly."""

from db.database import database
from snapshot_contracts import decode_config, decode_snapshot, encode_snapshot


def record_decision(payload):
    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        run = conn.execute("SELECT * FROM runs WHERE id=?", (payload.run_id,)).fetchone()
        if not run:
            raise LookupError("Run not found")
        if run["status"] != "COMPLETED":
            raise ValueError("A completed run is required")
        experiment = conn.execute(
            "SELECT final_evaluation_run_id FROM experiments WHERE id=?",
            (run["experiment_id"],),
        ).fetchone()
        if experiment["final_evaluation_run_id"]:
            raise ValueError(
                "Candidate decisions are frozen after final test evaluation is reserved"
            )
        validation = (
            decode_snapshot(run["validation_json"], "validation")
            if run["validation_json"]
            else None
        )
        if validation is None:
            metric = conn.execute(
                "SELECT val_loss,val_acc,epoch FROM epoch_metrics WHERE run_id=? "
                "ORDER BY val_acc DESC,epoch DESC LIMIT 1",
                (payload.run_id,),
            ).fetchone()
            if not metric:
                raise ValueError("A run with recorded validation evidence is required")
            validation = {
                "metric_set": "validation",
                "validation_loss": metric["val_loss"],
                "validation_accuracy": metric["val_acc"],
                "checkpoint_epoch": metric["epoch"],
            }
        if payload.status == "SELECTED":
            selected = conn.execute(
                """SELECT d.run_id FROM decisions d JOIN runs r ON r.id=d.run_id
                WHERE r.experiment_id=? AND d.status='SELECTED'
                AND d.id=(SELECT MAX(id) FROM decisions WHERE run_id=d.run_id) AND d.run_id!=?""",
                (run["experiment_id"], payload.run_id),
            ).fetchone()
            if selected:
                raise ValueError(
                    "Supersede the current Selected candidate before selecting another"
                )
        audits = [
            dict(row)
            for row in conn.execute(
                "SELECT a.*,j.status FROM audits a JOIN jobs j ON j.id=a.id "
                "WHERE a.run_id=? AND j.status='COMPLETED'",
                (payload.run_id,),
            )
        ]
        for audit in audits:
            audit["report"] = (
                decode_snapshot(audit["report"], "audit_report") if audit["report"] else None
            )
        evidence = {
            "metric_set": "validation",
            "validation": validation,
            "configuration": decode_config(run["config_json"]) if run["config_json"] else None,
            "environment": decode_snapshot(run["environment_json"], "environment")
            if run["environment_json"]
            else None,
            "dataset": decode_snapshot(run["dataset_json"], "dataset")
            if run["dataset_json"]
            else None,
            "checkpoint_sha256": validation.get("checkpoint_sha256"),
            "epoch_metrics": [
                dict(row)
                for row in conn.execute(
                    "SELECT epoch,train_loss,train_acc,val_loss,val_acc,learning_rate,epoch_time_sec "
                    "FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id",
                    (payload.run_id,),
                )
            ],
            "audits": audits,
        }
        details = payload.model_dump(exclude={"run_id", "status", "rationale"})
        cursor = conn.execute(
            "INSERT INTO decisions(run_id,status,rationale,details_json,evidence_json) VALUES(?,?,?,?,?)",
            (
                payload.run_id,
                payload.status,
                payload.rationale,
                encode_snapshot("decision_details", details),
                encode_snapshot("decision_evidence", evidence),
            ),
        )
        return {"message": "Decision recorded", "decision_id": cursor.lastrowid}
