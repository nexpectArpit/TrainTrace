"""Audits replay immutable configurations and preserve every participating run."""

import json
import statistics
from uuid import uuid4
from db.database import database
from jobs import insert_run
from tracking.tracker import (
    execute_run,
    cancelled,
    checkpoint_state_sha256,
    environment,
    event,
)
from tracking.evaluation_metrics import evaluate_candidate, benchmark_model_latency
from core.trainer import TrainingStopped
from core.dataset import get_test_dataloader, dataset_spec
from core.models import get_model_by_name
from config import DATA_DIR, get_default_device
from storage import write_json, sha256, find_run_artifact
from reporting import render_final_evaluation
from snapshot_contracts import decode_config, decode_snapshot, encode_snapshot
import torch


METRICS = ("train_loss", "train_acc", "val_loss", "val_acc", "learning_rate")


def execute_audit(payload, job_id):
    with database() as c:
        source = dict(c.execute("SELECT * FROM runs WHERE id=?", (payload["run_id"],)).fetchone())
    config = decode_config(source["config_json"])
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
                "validation_accuracy": evaluation["validation_accuracy"],
                "validation_loss": evaluation["validation_loss"],
                "model_state_sha256": evaluation["model_state_sha256"],
                "trajectory": metrics,
                "environment": decode_snapshot(row["environment_json"], "environment"),
                "dataset": decode_snapshot(row["dataset_json"], "dataset"),
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
        original_env = decode_snapshot(source["environment_json"], "environment")
        original_data = decode_snapshot(source["dataset_json"], "dataset")
        with database() as c:
            original_metrics = [
                {k: r[k] for k in METRICS}
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch", (source["id"],)
                )
            ]
        original_evaluation = decode_snapshot(source["validation_json"], "validation")
        original_checkpoint = find_run_artifact(
            source["id"], f"{source['id']}_best_checkpoint.pt", "checkpoints"
        )
        original_state_sha256 = checkpoint_state_sha256(original_checkpoint)
        parity = all(
            m["environment"] == original_env and m["dataset"] == original_data for m in members
        )
        exact = all(
            m["trajectory"] == original_metrics
            and m["validation_accuracy"] == original_evaluation["validation_accuracy"]
            and m["validation_loss"] == original_evaluation["validation_loss"]
            and m["model_state_sha256"] == original_state_sha256
            for m in members
        )
        report.update(
            passed=parity and exact,
            environment_match=parity,
            trajectory_match=exact,
            accuracy_delta=abs(a["validation_accuracy"] - b["validation_accuracy"]),
            comparison="Exact numeric trajectories, validation metrics, and model-state tensor hashes against original and both replays; timing excluded. The final test partition is not touched.",
            reason="Matched original conditions and measurements."
            if parity and exact
            else "Configuration/environment or measured trajectory differs; inspect members.",
        )
    else:
        values = [m["validation_accuracy"] for m in members]
        sample_std = statistics.stdev(values)
        t_critical_95 = {
            1: 12.706,
            2: 4.303,
            3: 3.182,
            4: 2.776,
            5: 2.571,
            6: 2.447,
            7: 2.365,
            8: 2.306,
            9: 2.262,
        }[len(values) - 1]
        margin = t_critical_95 * sample_std / (len(values) ** 0.5)
        report.update(
            metric_set="validation",
            mean_accuracy=statistics.mean(values),
            std_deviation=statistics.pstdev(values),
            min_accuracy=min(values),
            max_accuracy=max(values),
            spread=max(values) - min(values),
            sample_count=len(values),
            std_convention="Population standard deviation (ddof=0)",
            sample_std_deviation=sample_std,
            confidence_interval_95={
                "lower": statistics.mean(values) - margin,
                "upper": statistics.mean(values) + margin,
                "method": "two-sided Student t interval, sample standard deviation, df=N-1",
                "assumption": "approximately normal seed-level accuracy; N is small, so interval is descriptive and not a selection guarantee",
            },
            environment_match=all(
                m["environment"] == decode_snapshot(source["environment_json"], "environment")
                for m in members
            ),
            fixed_split=all(
                m["dataset"]["split_sha256"] == members[0]["dataset"]["split_sha256"]
                for m in members
            ),
        )
    report = json.loads(encode_snapshot("audit_report", report))
    write_json(source["id"], job_id, report)
    with database() as c:
        c.execute(
            "UPDATE audits SET report=? WHERE id=?",
            (encode_snapshot("audit_report", report), job_id),
        )
    return report


def execute_final_evaluation(payload, job_id):
    """Use the final test partition only after a selected candidate reserves it."""
    run_id = payload["run_id"]
    with database() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row or row["final_evaluation_job_id"] != job_id:
        raise ValueError("Final evaluation reservation does not match this job")
    if row["final_evaluation_status"] != "RUNNING":
        raise ValueError("Final evaluation is not in the running state")
    if not row["validation_json"] or not row["config_json"] or not row["dataset_json"]:
        raise ValueError("Run is missing the configuration or validation evidence")
    config = decode_config(row["config_json"])
    dataset_info = decode_snapshot(row["dataset_json"], "dataset")
    dataset_key = config["dataset_name"]
    _, spec = dataset_spec(dataset_key)
    test_loader = get_test_dataloader(
        dataset_key,
        batch_size=config["batch_size"],
        pretrained=bool(config.get("pretrained")),
    )
    actual_files = {
        str(path.relative_to(DATA_DIR)): sha256(path)
        for path in sorted((DATA_DIR / spec["source_dir"]).rglob("*"))
        if path.is_file()
    }
    training_file_hashes = dataset_info.get("file_hashes") or {}
    if any(actual_files.get(path) != digest for path, digest in training_file_hashes.items()):
        raise ValueError(
            "Training dataset files differ from their snapshot; final evaluation stopped"
        )
    if cancelled(job_id):
        raise TrainingStopped("Final evaluation stopped before the test pass")

    device = get_default_device()
    model = get_model_by_name(
        config["model_name"],
        num_classes=dataset_info["num_classes"],
        native_stem=bool(config.get("pretrained")),
        architecture_config=config.get("architecture_config"),
    ).to(device)
    checkpoint_path = find_run_artifact(run_id, f"{run_id}_best_checkpoint.pt", "checkpoints")
    validation = decode_snapshot(row["validation_json"], "validation")
    if not checkpoint_path.is_file() or sha256(checkpoint_path) != validation["checkpoint_sha256"]:
        raise ValueError("Selected checkpoint is missing or differs from validation evidence")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("run_id") != run_id:
        raise ValueError("Checkpoint identity mismatch")
    model.load_state_dict(checkpoint["model_state_dict"])
    evaluation = evaluate_candidate(
        model,
        test_loader,
        device,
        lambda: cancelled(job_id),
        num_classes=dataset_info["num_classes"],
    )
    input_size = dataset_info["preprocessing"]["size"][0]
    evaluation.update(
        checkpoint_sha256=sha256(checkpoint_path),
        checkpoint_epoch=checkpoint["epoch"],
        parameter_count=sum(parameter.numel() for parameter in model.parameters()),
        model_size_bytes=checkpoint_path.stat().st_size,
        dataset_name=dataset_info["name"],
        test_file_hashes=actual_files,
        environment=environment(),
        **benchmark_model_latency(model, device, input_size),
    )
    evaluation.update(
        render_final_evaluation(
            run_id,
            validation,
            evaluation,
            dataset_info.get("classes", [str(i) for i in range(dataset_info["num_classes"])]),
        )
    )
    write_json(run_id, "final_evaluation", evaluation)
    with database() as c:
        c.execute(
            "UPDATE runs SET final_evaluation_json=?,final_evaluation_status='COMPLETED',final_evaluation_error=NULL "
            "WHERE id=? AND final_evaluation_job_id=? AND final_evaluation_status='RUNNING'",
            (encode_snapshot("final_evaluation", evaluation), run_id, job_id),
        )
    event(run_id, f"Final test evaluation complete: {evaluation['test_accuracy']:.2f}%")
    return evaluation
