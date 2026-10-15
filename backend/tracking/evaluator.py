"""Audits replay immutable configurations and preserve every participating run."""

import json
import statistics
from uuid import uuid4
from db.database import database
from jobs import insert_run
from tracking.tracker import execute_run, cancelled
from core.trainer import TrainingStopped
from storage import write_json


METRICS = ("train_loss", "train_acc", "val_loss", "val_acc", "learning_rate")


def execute_audit(payload, job_id):
    with database() as c:
        source = dict(c.execute("SELECT * FROM runs WHERE id=?", (payload["run_id"],)).fetchone())
    config = json.loads(source["config_json"])
    seeds = [config["seed"], config["seed"]] if payload["protocol"] == "A" else payload["seeds"]
    members = []
    for seed in seeds:
        if cancelled(job_id):
            raise TrainingStopped("Audit stopped")
        child = {
            **config,
            "run_id": "replay_" + uuid4().hex,
            "seed": seed,
            "predecessor_run_id": None,
            "motivating_reason": "Audit replay of " + source["id"],
        }
        with database() as c:
            insert_run(c, child, job_id)
        evaluation = execute_run(child, job_id)
        with database() as c:
            row = dict(c.execute("SELECT * FROM runs WHERE id=?", (child["run_id"],)).fetchone())
            metrics = [
                {k: r[k] for k in METRICS}
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch", (child["run_id"],)
                )
            ]
        members.append(
            {
                "run_id": child["run_id"],
                "seed": seed,
                "test_accuracy": evaluation["test_accuracy"],
                "test_loss": evaluation["test_loss"],
                "trajectory": metrics,
                "environment": json.loads(row["environment_json"]),
                "dataset": json.loads(row["dataset_json"]),
            }
        )
    report = {
        "protocol": payload["protocol"],
        "source_run_id": source["id"],
        "members": members,
        "configuration": config,
        "accuracy_unit": "percent",
    }
    if payload["protocol"] == "A":
        a, b = members
        original_env = json.loads(source["environment_json"])
        original_data = json.loads(source["dataset_json"])
        with database() as c:
            original_metrics = [
                {k: r[k] for k in METRICS}
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch", (source["id"],)
                )
            ]
        original_evaluation = json.loads(source["evaluation_json"])
        parity = all(
            m["environment"] == original_env and m["dataset"] == original_data for m in members
        )
        exact = all(
            m["trajectory"] == original_metrics
            and m["test_accuracy"] == original_evaluation["test_accuracy"]
            and m["test_loss"] == original_evaluation["test_loss"]
            for m in members
        )
        report.update(
            passed=parity and exact,
            environment_match=parity,
            trajectory_match=exact,
            accuracy_delta=abs(a["test_accuracy"] - b["test_accuracy"]),
            comparison="Exact numeric trajectories and test loss/accuracy against original and both replays; timing excluded.",
            reason="Matched original conditions and measurements."
            if parity and exact
            else "Configuration/environment or measured trajectory differs; inspect members.",
        )
    else:
        values = [m["test_accuracy"] for m in members]
        report.update(
            mean_accuracy=statistics.mean(values),
            std_deviation=statistics.pstdev(values),
            min_accuracy=min(values),
            max_accuracy=max(values),
            spread=max(values) - min(values),
            sample_count=len(values),
            std_convention="Population standard deviation (ddof=0)",
            environment_match=all(
                m["environment"] == json.loads(source["environment_json"]) for m in members
            ),
            fixed_split=all(
                m["dataset"]["split_sha256"] == members[0]["dataset"]["split_sha256"]
                for m in members
            ),
        )
    write_json(source["id"], job_id, report)
    with database() as c:
        c.execute("UPDATE audits SET report=? WHERE id=?", (json.dumps(report), job_id))
    return report
