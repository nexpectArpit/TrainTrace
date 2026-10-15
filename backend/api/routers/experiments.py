"""Investigation management and evidence-backed, append-only decisions."""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from domain import ExperimentCreate, ExperimentUpdate, DecisionRecord
from db.database import database

router = APIRouter(prefix="/api/v1/experiments", tags=["Investigations"])
ExperimentCreateSchema = ExperimentCreate
DecisionRecordSchema = DecisionRecord


@router.get("/")
def list_experiments():
    with database() as c:
        return {
            "experiments": [
                dict(r) for r in c.execute("SELECT * FROM experiments ORDER BY created_at DESC,id")
            ]
        }


@router.post("/", status_code=201)
def create_experiment_endpoint(payload: ExperimentCreate):
    with database() as c:
        if c.execute("SELECT 1 FROM experiments WHERE id=?", (payload.id,)).fetchone():
            raise HTTPException(409, "Investigation ID already exists")
        if (
            payload.parent_run_id
            and not c.execute("SELECT 1 FROM runs WHERE id=?", (payload.parent_run_id,)).fetchone()
        ):
            raise HTTPException(404, "Parent run not found")
        c.execute(
            "INSERT INTO experiments(id,name,objective,hypothesis,target_accuracy,target_latency_ms,parent_run_id) VALUES(?,?,?,?,?,?,?)",
            (
                payload.id,
                payload.name,
                payload.objective,
                payload.hypothesis,
                payload.target_accuracy,
                payload.target_latency_ms,
                payload.parent_run_id,
            ),
        )
    return {"experiment_id": payload.id}


@router.get("/{exp_id}")
def get_experiment_endpoint(exp_id: str):
    with database() as c:
        row = c.execute("SELECT * FROM experiments WHERE id=?", (exp_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Investigation not found")
    return dict(row)


@router.patch("/{exp_id}")
def edit_experiment(exp_id: str, payload: ExperimentUpdate):
    get_experiment_endpoint(exp_id)
    with database() as c:
        fields = payload.model_dump()
        c.execute(
            "UPDATE experiments SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
            (*fields.values(), exp_id),
        )
    return get_experiment_endpoint(exp_id)


@router.get("/{exp_id}/runs/{run_id}/metrics")
def get_run_metrics_endpoint(exp_id: str, run_id: str):
    with database() as c:
        if not c.execute(
            "SELECT 1 FROM runs WHERE id=? AND experiment_id=?", (run_id, exp_id)
        ).fetchone():
            raise HTTPException(404, "Run not found in this investigation")
        return {
            "run_id": run_id,
            "epoch_metrics": [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id", (run_id,)
                )
            ],
        }


@router.post("/decisions", status_code=201)
def record_decision_endpoint(payload: DecisionRecord):
    with database() as c:
        c.execute("BEGIN IMMEDIATE")
        run = c.execute("SELECT * FROM runs WHERE id=?", (payload.run_id,)).fetchone()
        if not run:
            raise HTTPException(404, "Run not found")
        if run["status"] != "COMPLETED" or not run["evaluation_json"]:
            raise HTTPException(409, "A completed, holdout-evaluated run is required")
        if payload.status == "SELECTED":
            # Exactly one current Selected candidate within the investigation.
            selected = c.execute(
                """SELECT d.run_id FROM decisions d JOIN runs r ON r.id=d.run_id
                WHERE r.experiment_id=? AND d.status='SELECTED' AND d.id=(SELECT MAX(id) FROM decisions WHERE run_id=d.run_id) AND d.run_id!=?""",
                (run["experiment_id"], payload.run_id),
            ).fetchone()
            if selected:
                raise HTTPException(
                    409, "Supersede the current Selected candidate before selecting another"
                )
        audits = [
            dict(r)
            for r in c.execute(
                "SELECT a.*,j.status FROM audits a JOIN jobs j ON j.id=a.id WHERE a.run_id=? AND j.status='COMPLETED'",
                (payload.run_id,),
            )
        ]
        evidence = {"evaluation": json.loads(run["evaluation_json"]), "audits": audits}
        details = payload.model_dump(exclude={"run_id", "status", "rationale"})
        c.execute(
            "INSERT INTO decisions(run_id,status,rationale,details_json,evidence_json) VALUES(?,?,?,?,?)",
            (
                payload.run_id,
                payload.status,
                payload.rationale,
                json.dumps(details),
                json.dumps(evidence),
            ),
        )
        rows = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM decisions WHERE run_id=? ORDER BY id DESC", (payload.run_id,)
            )
        ]
    return {"message": "Decision recorded", "decisions": rows}


@router.get("/{exp_id}/report")
def decision_report(exp_id: str):
    exp = get_experiment_endpoint(exp_id)
    with database() as c:
        runs = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM runs WHERE experiment_id=? AND audit_id IS NULL ORDER BY created_at,id",
                (exp_id,),
            )
        ]
        models = [
            dict(r)
            for r in c.execute(
                "SELECT m.* FROM models m JOIN runs r ON r.id=m.run_id WHERE r.experiment_id=?",
                (exp_id,),
            )
        ]
        for run in runs:
            run["decisions"] = [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM decisions WHERE run_id=? ORDER BY id", (run["id"],)
                )
            ]
    lines = [
        f"# Model selection decision report: {exp['name']}",
        f"Objective: {exp['objective']}",
        f"Hypothesis: {exp['hypothesis'] or 'Unknown (legacy record)'}",
        f"Conclusion: {exp['conclusion'] or 'Not recorded'}",
    ]
    for r in runs:
        lines += [
            f"\n## {r['approach_name']} ({r['id']})",
            f"Execution: {r['status']}",
            f"Predecessor: {r['predecessor_run_id'] or 'None recorded'}",
            f"Motivation: {r['motivating_reason'] or 'Not recorded'}",
            "Evaluation: " + (r["evaluation_json"] or "Unverified legacy record"),
        ]
        for d in r["decisions"]:
            lines += [
                f"Decision {d['id']}: {d['status']} — {d['rationale']}",
                "Analysis: " + (d["details_json"] or "Not recorded"),
                "Evidence snapshot: " + (d["evidence_json"] or "Unknown (legacy record)"),
            ]
    lines += [
        "\n## Registered versions",
        *[
            f"{m['name']}:{m['version']} — {m['id']} — run {m['run_id']} — sha256 {m['sha256'] or 'unknown'}"
            for m in models
        ],
    ]
    return PlainTextResponse(
        "\n\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="decision-report.md"'},
    )
