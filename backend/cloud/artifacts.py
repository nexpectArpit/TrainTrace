"""Download, verify, and catalogue artifacts from a completed Kaggle run."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from cloud.credentials import get_authenticated_api
from config import STORAGE_DIR
from db.database import database
from snapshot_contracts import encode_snapshot
from storage import sha256, record_artifact, run_artifact_path, write_json

def download_and_ingest_kaggle_run(kernel_id: str, run_id: str) -> dict[str, Any]:
    """Download remote outputs to a temporary managed staging folder."""
    api, _ = get_authenticated_api()
    target_dir = STORAGE_DIR / "cloud_staging" / run_id / "output"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download kernel output files
    api.kernels_output(kernel_id, path=str(target_dir))

    results_file = target_dir / "traintrace_results.json"
    if results_file.is_file():
        with results_file.open() as f:
            summary = json.load(f)
        return {
            "success": True,
            "summary": summary,
            "output_dir": str(target_dir),
        }
    return {
        "success": False,
        "error": "traintrace_results.json was not found in downloaded Kaggle output",
    }


def ingest_completed_run(kernel_id: str, run_id: str, set_run_state, log_event) -> dict[str, Any]:
    # Ingest artifacts & metrics
    log_event("Cloud training complete! Downloading checkpoint and metrics from Kaggle...")
    ingest_result = download_and_ingest_kaggle_run(kernel_id, run_id)
    if not ingest_result.get("success"):
        raise RuntimeError(ingest_result.get("error", "Failed to ingest Kaggle outputs"))

    summary = ingest_result["summary"]
    history = summary.get("history", [])
    if not history:
        raise RuntimeError("Kaggle output contains no completed epoch history")

    with database() as c:
        for epoch in history:
            values = (
                run_id, epoch["epoch"], epoch["train_loss"], epoch["train_acc"],
                epoch["val_loss"], epoch["val_acc"], epoch["epoch_time_sec"],
                epoch["learning_rate"],
            )
            existing = c.execute(
                "SELECT id FROM epoch_metrics WHERE run_id=? AND epoch=?",
                (run_id, epoch["epoch"]),
            ).fetchone()
            if existing:
                c.execute(
                    "UPDATE epoch_metrics SET train_loss=?,train_acc=?,val_loss=?,val_acc=?,epoch_time_sec=?,learning_rate=? WHERE id=?",
                    values[2:] + (existing["id"],),
                )
            else:
                c.execute(
                    """INSERT INTO epoch_metrics(run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    values,
                )

    output_dir = Path(ingest_result["output_dir"])
    category_map = {
        f"{run_id}_best_checkpoint.pt": ("checkpoints", "best"),
        f"{run_id}_last_checkpoint.pt": ("checkpoints", "last"),
        f"{run_id}_metrics.csv": ("metrics", "metrics_csv"),
        f"{run_id}_progress.csv": ("metrics", "progress_csv"),
        f"{run_id}_split.json": ("data", "split"),
        f"{run_id}_training_curves.png": ("images", "training_curves_png"),
        f"{run_id}_dataset_preview.png": ("images", "dataset_preview_png"),
    }
    stored_paths = {}
    for filename, (category, kind) in category_map.items():
        source = output_dir / filename
        if not source.is_file():
            if filename in {f"{run_id}_best_checkpoint.pt", f"{run_id}_split.json", f"{run_id}_metrics.csv"}:
                raise RuntimeError(f"Required Kaggle output is missing: {filename}")
            continue
        target = run_artifact_path(run_id, filename, category)
        shutil.copy2(source, target)
        record_artifact(run_id, kind, target)
        stored_paths[filename] = target

    checkpoint_path = stored_paths[f"{run_id}_best_checkpoint.pt"]
    chk_sha = sha256(checkpoint_path)
    write_json(run_id, "cloud_summary", summary)
    remote_split_hash = summary.get("split_sha256")
    split_path = stored_paths[f"{run_id}_split.json"]
    if not remote_split_hash or sha256(split_path) != remote_split_hash:
        raise RuntimeError("Kaggle split artifact failed its recorded SHA-256 integrity check")
    write_json(run_id, "split", json.loads(stored_paths[f"{run_id}_split.json"].read_text()))
    split_path = run_artifact_path(run_id, f"{run_id}_split.json", "data")
    if sha256(split_path) != remote_split_hash:
        raise RuntimeError("Stored split artifact changed while being ingested")
    dataset_snapshot = summary.get("dataset")
    environment_snapshot = summary.get("environment")
    if not dataset_snapshot or not environment_snapshot:
        raise RuntimeError("Kaggle output is missing dataset or environment provenance")
    write_json(run_id, "dataset", dataset_snapshot)
    write_json(run_id, "environment", environment_snapshot)

    import torch
    checkpoint_data = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint_data.get("run_id") != run_id or checkpoint_data.get("epoch") != summary.get("best_epoch"):
        raise RuntimeError("Kaggle best checkpoint identity does not match its run summary")
    model_state = checkpoint_data.get("model_state_dict", {})
    parameter_count = sum(value.numel() for value in model_state.values() if hasattr(value, "numel"))
    state_digest = hashlib.sha256()
    for name, tensor in sorted(model_state.items()):
        value = tensor.detach().cpu().contiguous()
        state_digest.update(name.encode())
        state_digest.update(str(value.dtype).encode())
        state_digest.update(str(tuple(value.shape)).encode())
        state_digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())

    validation = {
        "metric_set": "validation",
        "validation_accuracy": summary.get("best_val_acc"),
        "validation_loss": summary.get("best_val_loss"),
        "checkpoint_sha256": chk_sha,
        "model_state_sha256": state_digest.hexdigest(),
        "checkpoint_epoch": summary.get("best_epoch"),
        "parameter_count": parameter_count,
        "model_size_bytes": checkpoint_path.stat().st_size,
        "cloud_provider": "Kaggle Cloud GPU",
        "gpu_device": summary.get("gpu_device", "Not reported"),
        "total_training_time_sec": summary.get("total_training_time_sec"),
    }
    set_run_state(
        status="COMPLETED",
        validation_json=encode_snapshot("validation", validation),
        dataset_json=encode_snapshot("dataset", dataset_snapshot),
        environment_json=encode_snapshot("environment", environment_snapshot),
    )
    log_event(f"Completed on Kaggle Cloud GPU: best validation accuracy {summary.get('best_val_acc'):.2f}%")
    return validation

