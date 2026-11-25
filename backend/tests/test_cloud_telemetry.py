"""Focused contract check for the separated Kaggle telemetry writer."""

import json
import time

from cloud.telemetry import ingest_kernel_logs
from db.database import database
from jobs import submit_run


def test_kaggle_markers_persist_progress_and_report_invalid_payload(config):
    submit_run(config)
    events = []
    states = []
    metric = {
        "epoch": 1, "batch_idx": 2, "total_batches": 4,
        "batch_loss": 0.5, "running_acc": 80.0,
        "samples_per_sec": 120.0, "device_memory_mb": 512.0,
        "gpu_memory_utilization_pct": 40.0, "gpu_temperature_c": 62.0,
    }
    epoch = {
        "epoch": 1, "train_loss": 0.5, "train_acc": 80.0,
        "val_loss": 0.6, "val_acc": 78.0, "epoch_time_sec": 9.0,
        "learning_rate": 0.001,
    }
    logs = "\n".join([
        "[TRAINTRACE_STAGE] " + json.dumps({"phase": "training", "message": "Epoch started"}),
        "[TRAINTRACE_METRIC] " + json.dumps(metric),
        "[TRAINTRACE_EPOCH] " + json.dumps(epoch),
        "[TRAINTRACE_METRIC] not-json",
    ])
    seen = set()
    for _ in range(2):
        ingest_kernel_logs(
            logs, seen, run_id=config.run_id, payload=config.model_dump(),
            kernel_id="example/kernel", remote_status="RUNNING",
            poll_start=time.time(), set_run_state=lambda **fields: states.append(fields),
            log_event=events.append,
        )
    with database() as conn:
        sample = conn.execute(
            "SELECT gpu_memory_utilization_pct,gpu_temperature_c FROM run_progress_samples WHERE run_id=?",
            (config.run_id,),
        ).fetchone()
        saved_epoch = conn.execute(
            "SELECT val_acc FROM epoch_metrics WHERE run_id=? AND epoch=1",
            (config.run_id,),
        ).fetchone()
    assert sample["gpu_memory_utilization_pct"] == 40.0
    assert sample["gpu_temperature_c"] == 62.0
    assert saved_epoch["val_acc"] == 78.0
    assert len(states) == 2
    assert len([event for event in events if "Could not ingest" in event]) == 1
