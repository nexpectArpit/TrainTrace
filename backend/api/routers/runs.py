"""Execution, cancellation, live state and comparison endpoints."""

import json
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from domain import LaunchRun, AuditRequest, FinalEvaluationRequest
from db.database import database
from jobs import submit_run, submit_audit, submit_final_evaluation, stop_job
from config import ARTIFACTS_DIR
from storage import sha256, resolve_managed_path
from services.run_service import run_detail as get_run_detail, compare_runs, search_tags
from notebook_export import build_notebook, model_source_text

router = APIRouter(prefix="/api/v1/runs", tags=["Runs and audits"])
LaunchRunSchema = LaunchRun
ProtocolAAuditSchema = ProtocolBAuditSchema = AuditRequest


def invoke(action, *args):
    try:
        return action(*args)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


def detail(run_id):
    run = get_run_detail(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/{run_id}/export-notebook")
def export_run_notebook(run_id: str):
    """Download a standalone Jupyter notebook prefilled with this run's settings."""
    run = detail(run_id)
    config = run.get("config") or {}
    if not config:
        raise HTTPException(409, "This legacy run has no saved configuration to export")
    notebook = invoke(build_notebook, run, model_source_text())
    return Response(
        content=notebook,
        media_type="application/x-ipynb+json",
        headers={"Content-Disposition": f'attachment; filename="traintrace_{run_id}.ipynb"'},
    )


@router.post("/launch", status_code=202)
def launch_run_endpoint(payload: LaunchRun):
    return invoke(submit_run, payload)


@router.post("/audit/protocol-a", status_code=202)
def audit_protocol_a_endpoint(payload: AuditRequest):
    return invoke(submit_audit, payload, "A")


@router.post("/audit/protocol-b", status_code=202)
def audit_protocol_b_endpoint(payload: AuditRequest):
    return invoke(submit_audit, payload, "B")


@router.post("/final-evaluation", status_code=202)
def final_evaluation_endpoint(payload: FinalEvaluationRequest):
    return invoke(submit_final_evaluation, payload)


@router.post("/jobs/{job_id}/stop")
def stop(job_id: str):
    return invoke(stop_job, job_id)


@router.get("/jobs")
def jobs():
    with database() as c:
        return {
            "jobs": [
                dict(r)
                for r in c.execute(
                    "SELECT id,kind,status,error,cancel_requested,created_at,updated_at FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT 100"
                )
            ]
        }


@router.get("/search")
def search_by_tag(
    tag_key: str | None = Query(None, pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"),
    tag_value: str | None = Query(None, min_length=1, max_length=256),
    search: str = Query("", max_length=256),
    dataset_name: str = Query("", pattern="^(|cifar10|cifar100|mnist|fashion_mnist|svhn)$"),
    architecture: str = Query("", pattern="^(|custom_cnn|resnet18|mobilenet_v2|efficientnet_b0)$"),
    status: str = Query("", max_length=32),
    seed: int | None = Query(None, ge=0, le=2**32 - 1),
    accuracy_min: float | None = Query(None, ge=0, le=100),
    accuracy_max: float | None = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search across runs, investigations and models by exact tag or metadata filters."""
    if bool(tag_key) != bool(tag_value):
        raise HTTPException(422, "tag_key and tag_value must be supplied together")
    if accuracy_min is not None and accuracy_max is not None and accuracy_min > accuracy_max:
        raise HTTPException(422, "accuracy_min cannot exceed accuracy_max")
    return search_tags(
        tag_key,
        tag_value,
        search=search,
        dataset_name=dataset_name,
        architecture=architecture,
        status=status,
        seed=seed,
        accuracy_min=accuracy_min,
        accuracy_max=accuracy_max,
        limit=limit,
        offset=offset,
    )


@router.get("/artifacts/{artifact_id}")
def download_artifact(artifact_id: str):
    with database() as c:
        row = c.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Artifact not found")
    try:
        path = resolve_managed_path(ARTIFACTS_DIR, row["path"])
    except ValueError:
        raise HTTPException(404, "Managed artifact is unavailable") from None
    if not path.is_file():
        raise HTTPException(404, "Managed artifact is unavailable")
    if sha256(path) != row["sha256"]:
        raise HTTPException(409, "Artifact checksum mismatch")
    return FileResponse(path, filename=path.name)


@router.get("/compare/{exp_id}")
def compare_experiment_runs(
    exp_id: str,
    search: str = "",
    architecture: str = "",
    status: str = "",
    seed: int | None = Query(None, ge=0, le=2**32 - 1),
    accuracy_min: float | None = Query(None, ge=0, le=100),
    accuracy_max: float | None = Query(None, ge=0, le=100),
    validation_accuracy_min: float | None = Query(None, ge=0, le=100),
    validation_accuracy_max: float | None = Query(None, ge=0, le=100),
    dataset_name: str = Query("", pattern="^(|cifar10|cifar100|mnist|fashion_mnist|svhn)$"),
    optimizer: str = Query("", pattern="^(|adamw|sgd)$"),
    architecture_depth: int | None = Query(None, ge=2, le=6),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    low = validation_accuracy_min if validation_accuracy_min is not None else accuracy_min
    high = validation_accuracy_max if validation_accuracy_max is not None else accuracy_max
    exp, total, ids = compare_runs(
        exp_id,
        search=search,
        architecture=architecture,
        status=status,
        seed=seed,
        accuracy_min=low,
        accuracy_max=high,
        dataset_name=dataset_name,
        optimizer=optimizer,
        architecture_depth=architecture_depth,
        limit=limit,
        offset=offset,
    )
    if exp is None:
        raise HTTPException(404, "Investigation not found")
    return {
        "experiment": exp,
        "comparison_matrix": [detail(run_id) for run_id in ids],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{run_id}/live-status")
def get_run_live_status_endpoint(run_id: str, after: int = Query(0, ge=0)):
    with database() as c:
        job = c.execute("SELECT status,cancel_requested FROM jobs WHERE id=?", (run_id,)).fetchone()
        # Repair legacy stop/cancel records where the job reached a terminal
        # state but the run row was left RUNNING by an older worker version.
        if job and job["status"] in ("STOPPED", "FAILED"):
            c.execute(
                "UPDATE runs SET status=?,error=COALESCE(error,?) WHERE id=? AND status IN ('QUEUED','RUNNING','EVALUATING')",
                (
                    job["status"],
                    "Job stopped." if job["status"] == "STOPPED" else "Job failed.",
                    run_id,
                ),
            )
        events = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT 200",
                (run_id, after),
            )
        ]
        samples = [
            dict(r)
            for r in c.execute(
                "SELECT epoch,batch_idx,total_batches,batch_loss,running_acc,samples_per_sec,device_memory_mb,worker_cpu_percent,peak_rss_mb,gpu_utilization_pct,gpu_memory_used_mb,gpu_memory_total_mb,gpu_memory_utilization_pct,gpu_temperature_c,gpu_power_watts,observed_at "
                "FROM run_progress_samples WHERE run_id=? ORDER BY id DESC LIMIT 500",
                (run_id,),
            )
        ][::-1]
    run = detail(run_id)
    return {
        "run_id": run_id,
        "cancel_requested": bool(job and job["status"] == "RUNNING" and job["cancel_requested"]),
        "job_status": job["status"] if job else None,
        "status": run["status"],
        "error": run["error"],
        "progress": run["progress"],
        "progress_samples": samples,
        "epochs_completed": len(run["metrics"]),
        "all_metrics": run["metrics"],
        "events": events,
        "next_cursor": events[-1]["id"] if events else after,
    }


@router.get("/{run_id}")
def run_detail(run_id: str):
    return detail(run_id)


@router.post("/{run_id}/telemetry")
def record_run_telemetry(run_id: str, payload: dict[str, Any]):
    """Ingest real-time batch telemetry from remote runners (e.g., Kaggle Cloud GPU)."""
    with database() as c:
        row = c.execute(
            "SELECT id, status, progress_json FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Run not found")
        c.execute(
            """INSERT OR IGNORE INTO run_progress_samples(
                run_id, epoch, batch_idx, total_batches, batch_loss, running_acc,
                samples_per_sec, device_memory_mb, worker_cpu_percent, peak_rss_mb,
                gpu_utilization_pct, gpu_memory_used_mb, gpu_memory_total_mb, gpu_memory_utilization_pct,
                gpu_temperature_c, gpu_power_watts, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                run_id,
                payload.get("epoch", 1),
                payload.get("batch_idx", 1),
                payload.get("total_batches", 1),
                float(payload.get("batch_loss", 0.0)),
                float(payload.get("running_acc", 0.0)),
                float(payload.get("samples_per_sec", 0.0)),
                float(payload.get("device_memory_mb", 0.0)),
                payload.get("worker_cpu_percent"),
                payload.get("peak_rss_mb"),
                payload.get("gpu_utilization_pct"),
                payload.get("gpu_memory_used_mb"),
                payload.get("gpu_memory_total_mb"),
                payload.get("gpu_memory_utilization_pct"),
                payload.get("gpu_temperature_c"),
                payload.get("gpu_power_watts"),
            ),
        )
        current_progress = {}
        if row["progress_json"]:
            try:
                current_progress = json.loads(row["progress_json"])
            except Exception:
                pass
        current_progress.update(
            {
                "phase": "training",
                "epoch": payload.get("epoch", current_progress.get("epoch", 1)),
                "batch_idx": payload.get("batch_idx", current_progress.get("batch_idx", 1)),
                "total_batches": payload.get(
                    "total_batches", current_progress.get("total_batches", 1)
                ),
                "batch_loss": float(payload.get("batch_loss", 0.0)),
                "running_acc": float(payload.get("running_acc", 0.0)),
                "samples_per_sec": float(payload.get("samples_per_sec", 0.0)),
                "device_memory_mb": float(payload.get("device_memory_mb", 0.0)),
                "lr": payload.get("learning_rate", current_progress.get("lr")),
            }
        )
        for key in (
            "worker_cpu_percent",
            "peak_rss_mb",
            "gpu_utilization_pct",
            "gpu_memory_used_mb",
            "gpu_memory_total_mb",
            "gpu_memory_utilization_pct",
            "gpu_temperature_c",
            "gpu_power_watts",
        ):
            if payload.get(key) is not None:
                current_progress[key] = payload[key]
        c.execute(
            "UPDATE runs SET progress_json=? WHERE id=?", (json.dumps(current_progress), run_id)
        )
    return {"status": "ok"}


@router.post("/{run_id}/epoch-telemetry")
def record_run_epoch_telemetry(run_id: str, payload: dict[str, Any]):
    """Ingest epoch metrics from remote runners (e.g., Kaggle Cloud GPU)."""
    with database() as c:
        row = c.execute("SELECT id FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Run not found")
        values = (
            run_id,
            payload["epoch"],
            float(payload["train_loss"]),
            float(payload["train_acc"]),
            float(payload["val_loss"]),
            float(payload["val_acc"]),
            float(payload.get("epoch_time_sec", 0.0)),
            float(payload.get("learning_rate", 0.001)),
        )
        existing = c.execute(
            "SELECT id FROM epoch_metrics WHERE run_id=? AND epoch=?",
            (run_id, payload["epoch"]),
        ).fetchone()
        if existing:
            c.execute(
                """UPDATE epoch_metrics SET train_loss=?,train_acc=?,val_loss=?,val_acc=?,
                   epoch_time_sec=?,learning_rate=? WHERE id=?""",
                values[2:] + (existing["id"],),
            )
        else:
            c.execute(
                """INSERT INTO epoch_metrics(
                    run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate
                ) VALUES(?,?,?,?,?,?,?,?)""",
                values,
            )
    return {"status": "ok"}
