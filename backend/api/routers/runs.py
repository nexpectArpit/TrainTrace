"""Execution, cancellation, live state and comparison endpoints."""

import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from domain import LaunchRun, AuditRequest
from db.database import database
from jobs import submit_run, submit_audit, stop_job
from config import ARTIFACTS_DIR
from storage import sha256

router = APIRouter(prefix="/api/v1/runs", tags=["Runs and audits"])
LaunchRunSchema = LaunchRun
ProtocolAAuditSchema = ProtocolBAuditSchema = AuditRequest


def invoke(action, *args):
    try:
        return action(*args)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


def detail(run_id):
    with database() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Run not found")
        run = dict(row)
        run["metrics"] = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id", (run_id,)
            )
        ]
        run["decisions"] = [
            dict(r)
            for r in c.execute("SELECT * FROM decisions WHERE run_id=? ORDER BY id DESC", (run_id,))
        ]
        run["artifacts"] = [
            dict(r)
            for r in c.execute(
                "SELECT id,kind,sha256,size_bytes,created_at FROM artifacts WHERE run_id=? ORDER BY created_at,id",
                (run_id,),
            )
        ]
        run["audits"] = [
            dict(r)
            for r in c.execute(
                "SELECT a.*,j.status,j.error FROM audits a JOIN jobs j ON j.id=a.id WHERE a.run_id=? ORDER BY a.created_at DESC,a.id",
                (run_id,),
            )
        ]
        for audit in run["audits"]:
            audit["members"] = [
                dict(r)
                for r in c.execute(
                    "SELECT id,seed,status,error FROM runs WHERE audit_id=? ORDER BY created_at,rowid",
                    (audit["id"],),
                )
            ]
    for field in ["config", "environment", "dataset", "evaluation", "progress"]:
        run[field] = json.loads(run.pop(field + "_json")) if run.get(field + "_json") else None
    for d in run["decisions"]:
        d["details"] = json.loads(d.pop("details_json")) if d.get("details_json") else None
        d["evidence"] = json.loads(d.pop("evidence_json")) if d.get("evidence_json") else None
    for a in run["audits"]:
        a["report"] = json.loads(a["report"]) if a["report"] else None
    run["run_id"] = run["id"]
    run["latest_decision"] = run["decisions"][0] if run["decisions"] else None
    run["best_val_accuracy"] = max((m["val_acc"] for m in run["metrics"]), default=None)
    run["total_duration_sec"] = sum(m["epoch_time_sec"] for m in run["metrics"])
    last = run["metrics"][-1] if run["metrics"] else None
    run["overfitting_gap"] = last["train_acc"] - last["val_acc"] if last else None
    return run


@router.post("/launch", status_code=202)
def launch_run_endpoint(payload: LaunchRun):
    return invoke(submit_run, payload)


@router.post("/audit/protocol-a", status_code=202)
def audit_protocol_a_endpoint(payload: AuditRequest):
    return invoke(submit_audit, payload, "A")


@router.post("/audit/protocol-b", status_code=202)
def audit_protocol_b_endpoint(payload: AuditRequest):
    return invoke(submit_audit, payload, "B")


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


@router.get("/artifacts/{artifact_id}")
def download_artifact(artifact_id: str):
    from pathlib import Path

    with database() as c:
        row = c.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Artifact not found")
    path = Path(row["path"]).resolve()
    if not path.is_relative_to(ARTIFACTS_DIR.resolve()) or not path.is_file():
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
    seed: int | None = None,
    accuracy_min: float | None = None,
    accuracy_max: float | None = None,
):
    with database() as c:
        exp = c.execute("SELECT * FROM experiments WHERE id=?", (exp_id,)).fetchone()
        if not exp:
            raise HTTPException(404, "Investigation not found")
        ids = [
            r[0]
            for r in c.execute(
                "SELECT id FROM runs WHERE experiment_id=? AND audit_id IS NULL ORDER BY created_at DESC,id",
                (exp_id,),
            )
        ]
    runs = [detail(i) for i in ids]
    runs = [
        r
        for r in runs
        if (not search or search.lower() in (r["id"] + " " + r["approach_name"]).lower())
        and (not architecture or r["model_architecture"] == architecture)
        and (
            not status
            or r["status"] == status
            or (r["latest_decision"] or {}).get("status") == status
        )
        and (seed is None or r["seed"] == seed)
        and (
            accuracy_min is None
            or r["evaluation"]
            and r["evaluation"]["test_accuracy"] >= accuracy_min
        )
        and (
            accuracy_max is None
            or r["evaluation"]
            and r["evaluation"]["test_accuracy"] <= accuracy_max
        )
    ]
    return {"experiment": dict(exp), "comparison_matrix": runs}


@router.get("/{run_id}/live-status")
def get_run_live_status_endpoint(run_id: str, after: int = Query(0, ge=0)):
    run = detail(run_id)
    with database() as c:
        events = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT 200",
                (run_id, after),
            )
        ]
    return {
        "run_id": run_id,
        "status": run["status"],
        "error": run["error"],
        "progress": run["progress"],
        "epochs_completed": len(run["metrics"]),
        "all_metrics": run["metrics"],
        "events": events,
        "next_cursor": events[-1]["id"] if events else after,
    }


@router.get("/{run_id}")
def run_detail(run_id: str):
    return detail(run_id)
