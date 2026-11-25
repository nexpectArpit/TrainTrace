"""Parse Kaggle log markers and persist observable training progress."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from db.database import database

METRIC_FIELDS = (
    "worker_cpu_percent", "peak_rss_mb", "gpu_utilization_pct",
    "gpu_memory_used_mb", "gpu_memory_total_mb", "gpu_memory_utilization_pct",
    "gpu_temperature_c", "gpu_power_watts",
)


def _save_batch(run_id: str, metric: dict, payload: dict, kernel_id: str,
                remote_status: str, elapsed: float, set_run_state: Callable) -> None:
    with database() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO run_progress_samples(
                run_id,epoch,batch_idx,total_batches,batch_loss,running_acc,
                samples_per_sec,device_memory_mb,worker_cpu_percent,peak_rss_mb,
                gpu_utilization_pct,gpu_memory_used_mb,gpu_memory_total_mb,
                gpu_memory_utilization_pct,gpu_temperature_c,gpu_power_watts,observed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (
                run_id, metric["epoch"], metric["batch_idx"], metric["total_batches"],
                metric["batch_loss"], metric["running_acc"],
                metric.get("samples_per_sec"), metric.get("device_memory_mb"),
                *(metric.get(key) for key in METRIC_FIELDS),
            ),
        )
    progress = {
        "phase": "training", "provider": "Kaggle Cloud GPU", "kernel_id": kernel_id,
        "remote_status": remote_status, "epoch": metric["epoch"],
        "total_epochs": payload["epochs"], "batch_idx": metric["batch_idx"],
        "total_batches": metric["total_batches"], "batch_loss": metric["batch_loss"],
        "running_acc": metric["running_acc"],
        "lr": metric.get("learning_rate", payload["learning_rate"]),
        "samples_per_sec": metric.get("samples_per_sec"),
        "device_memory_mb": metric.get("device_memory_mb"),
        **{key: metric[key] for key in METRIC_FIELDS if metric.get(key) is not None},
        "elapsed_seconds": elapsed,
        "message": f"Kaggle GPU Training: Epoch {metric['epoch']} · Batch {metric['batch_idx']}/{metric['total_batches']} (Loss {metric['batch_loss']:.3f})",
    }
    set_run_state(progress_json=json.dumps(progress, allow_nan=False))


def _save_epoch(run_id: str, epoch: dict, payload: dict, log_event: Callable) -> None:
    values = (
        run_id, epoch["epoch"], epoch["train_loss"], epoch["train_acc"],
        epoch["val_loss"], epoch["val_acc"], epoch.get("epoch_time_sec"),
        epoch.get("learning_rate", payload["learning_rate"]),
    )
    with database() as conn:
        existing = conn.execute(
            "SELECT id FROM epoch_metrics WHERE run_id=? AND epoch=?",
            (run_id, epoch["epoch"]),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE epoch_metrics SET train_loss=?,train_acc=?,val_loss=?,val_acc=?,epoch_time_sec=?,learning_rate=? WHERE id=?",
                values[2:] + (existing["id"],),
            )
        else:
            conn.execute(
                """INSERT INTO epoch_metrics(
                    run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate
                ) VALUES(?,?,?,?,?,?,?,?)""",
                values,
            )
    log_event(
        f"Kaggle GPU Epoch {epoch['epoch']} complete: "
        f"Train Acc={epoch['train_acc']:.2f}%, Val Acc={epoch['val_acc']:.2f}%"
    )


def ingest_kernel_logs(raw_logs: str, seen_lines: set[str], *, run_id: str,
                       payload: dict, kernel_id: str, remote_status: str,
                       poll_start: float, set_run_state: Callable,
                       log_event: Callable) -> None:
    """Process each marker once; report malformed telemetry without hiding it."""
    if not isinstance(raw_logs, str):
        raise TypeError(f"Kaggle logs returned {type(raw_logs).__name__}, expected text")
    for raw_line in raw_logs.splitlines():
        line = raw_line.strip()
        if not line or line in seen_lines:
            continue
        seen_lines.add(line)
        marker = next((prefix for prefix in (
            "[TRAINTRACE_STAGE]", "[TRAINTRACE_METRIC]", "[TRAINTRACE_EPOCH]"
        ) if line.startswith(prefix)), None)
        if marker is None:
            continue
        try:
            record = json.loads(line[len(marker):].strip())
            if not isinstance(record, dict):
                raise ValueError("marker payload must be a JSON object")
            if marker == "[TRAINTRACE_STAGE]":
                set_run_state(progress_json=json.dumps({
                    **record, "provider": "Kaggle Cloud GPU", "kernel_id": kernel_id,
                    "remote_status": remote_status,
                    "elapsed_seconds": round(time.time() - poll_start, 1),
                }, allow_nan=False))
                log_event(record.get("message") or "Kaggle worker advanced to the next stage.")
            elif marker == "[TRAINTRACE_METRIC]":
                _save_batch(run_id, record, payload, kernel_id, remote_status,
                            round(time.time() - poll_start, 1), set_run_state)
            else:
                _save_epoch(run_id, record, payload, log_event)
        except Exception as exc:
            log_event(f"Could not ingest {marker} telemetry: {type(exc).__name__}: {exc}")
