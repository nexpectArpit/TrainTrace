"""Investigation management and evidence-backed, append-only decisions."""

import json
import csv
from io import StringIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from domain import ExperimentCreate, ExperimentUpdate, DecisionRecord
from db.database import database
from snapshot_contracts import decode_config, decode_snapshot
from services.decision_service import record_decision

router = APIRouter(prefix="/api/v1/experiments", tags=["Investigations"])
ExperimentCreateSchema = ExperimentCreate
DecisionRecordSchema = DecisionRecord


@router.get("/")
def list_experiments():
    with database() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM experiments ORDER BY created_at DESC,id")]
    for row in rows:
        row["tags"] = json.loads(row.pop("tags_json", "{}"))
    return {"experiments": rows}


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
            "INSERT INTO experiments(id,name,objective,hypothesis,target_accuracy,target_latency_ms,parent_run_id,tags_json) VALUES(?,?,?,?,?,?,?,?)",
            (
                payload.id,
                payload.name,
                payload.objective,
                payload.hypothesis,
                payload.target_accuracy,
                payload.target_latency_ms,
                payload.parent_run_id,
                json.dumps(payload.tags),
            ),
        )
    return {"experiment_id": payload.id}


@router.get("/{exp_id}")
def get_experiment_endpoint(exp_id: str):
    with database() as c:
        row = c.execute("SELECT * FROM experiments WHERE id=?", (exp_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Investigation not found")
    result = dict(row)
    result["tags"] = json.loads(result.pop("tags_json", "{}"))
    return result


@router.patch("/{exp_id}")
def edit_experiment(exp_id: str, payload: ExperimentUpdate):
    get_experiment_endpoint(exp_id)
    with database() as c:
        fields = payload.model_dump(exclude={"tags"})
        if payload.tags is not None:
            fields["tags_json"] = json.dumps(payload.tags)
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
    try:
        return record_decision(payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


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
            run["metrics"] = [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id",
                    (run["id"],),
                )
            ]
            run["audits"] = [
                dict(r)
                for r in c.execute(
                    "SELECT a.*,j.status FROM audits a JOIN jobs j ON j.id=a.id WHERE a.run_id=? ORDER BY a.created_at,a.id",
                    (run["id"],),
                )
            ]

    def md(value):
        return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")

    def config_for(run):
        return decode_config(run["config_json"]) if run.get("config_json") else {}

    def evaluation_for(run):
        evaluation = decode_snapshot(run["final_evaluation_json"], "final_evaluation") if run.get("final_evaluation_json") else {}
        latest_decision = run["decisions"][-1]["status"] if run.get("decisions") else None
        return evaluation if run.get("final_evaluation_status") == "COMPLETED" and latest_decision == "SELECTED" and not evaluation.get("legacy_preselection_test_exposure") else {}

    def validation_for(run):
        return decode_snapshot(run["validation_json"], "validation") if run.get("validation_json") else {}

    lines = [
        f"# Model selection decision report: {exp['name']}",
        f"Objective: {exp['objective']}",
        f"Hypothesis: {exp['hypothesis'] or 'Unknown (legacy record)'}",
        f"Conclusion: {exp['conclusion'] or 'Not recorded'}",
        "",
        "## Candidate comparison",
        "| Candidate | Dataset | Architecture | Status | Best validation % | Validation loss | Final holdout accuracy % | Parameters |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for r in runs:
        config = config_for(r)
        evaluation = evaluation_for(r)
        validation = validation_for(r)
        dataset = decode_snapshot(r["dataset_json"], "dataset") if r.get("dataset_json") else {}
        best_validation = max((m["val_acc"] for m in r["metrics"]), default=None)
        lines.append(
            "| "
            + " | ".join(
                md(value)
                for value in [
                    r["approach_name"],
                    dataset.get("name", config.get("dataset_name", "Unknown")),
                    r["model_architecture"],
                    r["status"],
                    validation.get("validation_accuracy", best_validation),
                    validation.get("validation_loss"),
                    evaluation.get("test_accuracy"),
                    evaluation.get("parameter_count"),
                ]
            )
            + " |"
        )
    for r in runs:
        config = config_for(r)
        lines += [
            f"\n## {r['approach_name']} ({r['id']})",
            f"Execution: {r['status']}",
            f"Dataset: {(decode_snapshot(r['dataset_json'], 'dataset') if r.get('dataset_json') else {}).get('name', config.get('dataset_name', 'Unknown'))}",
            f"Predecessor: {r['predecessor_run_id'] or 'None recorded'}",
            f"Motivation: {r['motivating_reason'] or 'Not recorded'}",
            "### Configuration",
            "```json",
            json.dumps(config, indent=2),
            "```",
            "### Epoch metrics",
            "| Epoch | Train loss | Train accuracy % | Validation loss | Validation accuracy % | Learning rate | Seconds |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for metric in r["metrics"]:
            lines.append(
                "| "
                + " | ".join(
                    md(metric.get(key))
                    for key in [
                        "epoch",
                        "train_loss",
                        "train_acc",
                        "val_loss",
                        "val_acc",
                        "learning_rate",
                        "epoch_time_sec",
                    ]
                )
                + " |"
            )
        evaluation = evaluation_for(r)
        historical_evaluation = decode_snapshot(r["final_evaluation_json"], "final_evaluation") if r.get("final_evaluation_json") else {}
        lines += [
            "### Final test evaluation",
            "Historical test exposure from the previous workflow; not a valid post-selection result."
            if historical_evaluation.get("legacy_preselection_test_exposure")
            else "Post-selection evaluation." if evaluation else "Sealed, incomplete, or no longer eligible for display.",
            "```json",
        ]
        lines.append(
            json.dumps(evaluation, indent=2)
            if evaluation
            else "No eligible final holdout values are displayed."
        )
        lines.append("```")
        for audit in r["audits"]:
            lines += [
                f"### Protocol {audit['protocol']} audit ({audit['status']})",
                "```json",
                audit.get("report") or "No completed report",
                "```",
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


@router.get("/{exp_id}/report.csv")
def metrics_report_csv(exp_id: str):
    exp = get_experiment_endpoint(exp_id)
    output = StringIO(newline="")
    fields = [
        "experiment_id",
        "experiment_name",
        "run_id",
        "approach_name",
        "dataset",
        "architecture",
        "architecture_config",
        "optimizer",
        "seed",
        "run_status",
        "epoch",
        "train_loss",
        "train_accuracy_percent",
        "validation_loss",
        "validation_accuracy_percent",
        "learning_rate",
        "epoch_seconds",
        "holdout_accuracy_percent",
        "holdout_loss",
        "macro_f1",
        "test_metric_status",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    with database() as c:
        runs = [
            dict(row)
            for row in c.execute(
                "SELECT * FROM runs WHERE experiment_id=? AND audit_id IS NULL ORDER BY created_at,id",
                (exp_id,),
            )
        ]
        for run in runs:
            config = decode_config(run["config_json"]) if run.get("config_json") else {}
            dataset = decode_snapshot(run["dataset_json"], "dataset") if run.get("dataset_json") else {}
            raw_evaluation = decode_snapshot(run["final_evaluation_json"], "final_evaluation") if run.get("final_evaluation_json") else {}
            latest_decision = c.execute("SELECT status FROM decisions WHERE run_id=? ORDER BY id DESC LIMIT 1", (run["id"],)).fetchone()
            eligible = run.get("final_evaluation_status") == "COMPLETED" and latest_decision and latest_decision["status"] == "SELECTED" and not raw_evaluation.get("legacy_preselection_test_exposure")
            evaluation = raw_evaluation if eligible else {}
            metrics = [
                dict(row)
                for row in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id", (run["id"],)
                )
            ] or [{}]
            for metric in metrics:
                writer.writerow(
                    {
                        "experiment_id": exp_id,
                        "experiment_name": exp["name"],
                        "run_id": run["id"],
                        "approach_name": run["approach_name"],
                        "dataset": dataset.get("name", config.get("dataset_name", "Unknown")),
                        "architecture": run["model_architecture"],
                        "architecture_config": json.dumps(config.get("architecture_config", {})),
                        "optimizer": config.get("optimizer", ""),
                        "seed": run["seed"],
                        "run_status": run["status"],
                        "epoch": metric.get("epoch", ""),
                        "train_loss": metric.get("train_loss", ""),
                        "train_accuracy_percent": metric.get("train_acc", ""),
                        "validation_loss": metric.get("val_loss", ""),
                        "validation_accuracy_percent": metric.get("val_acc", ""),
                        "learning_rate": metric.get("learning_rate", ""),
                        "epoch_seconds": metric.get("epoch_time_sec", ""),
                        "holdout_accuracy_percent": evaluation.get("test_accuracy", ""),
                        "holdout_loss": evaluation.get("test_loss", ""),
                        "macro_f1": evaluation.get("f1_macro", ""),
                        "test_metric_status": (
                            "HISTORICAL_PRESELECTION"
                            if raw_evaluation.get("legacy_preselection_test_exposure")
                            else "FINAL_POSTSELECTION"
                            if evaluation
                            else "WITHHELD"
                            if raw_evaluation
                            else "NOT_EVALUATED"
                        ),
                    }
                )
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="traintrace-metrics-report.csv"'},
    )
