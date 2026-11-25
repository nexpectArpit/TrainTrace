"""Run, comparison and tag-search persistence queries."""

import json

from db.database import database
from snapshot_contracts import decode_config, decode_snapshot


def get_run(run_id):
    with database() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        run = dict(row)
        run["metrics"] = [dict(r) for r in conn.execute(
            "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id", (run_id,)
        )]
        run["decisions"] = [dict(r) for r in conn.execute(
            "SELECT * FROM decisions WHERE run_id=? ORDER BY id DESC", (run_id,)
        )]
        run["artifacts"] = [dict(r) for r in conn.execute(
            "SELECT id,kind,sha256,size_bytes,created_at FROM artifacts WHERE run_id=? ORDER BY created_at,id",
            (run_id,),
        )]
        run["audits"] = [dict(r) for r in conn.execute(
            "SELECT a.*,j.status,j.error FROM audits a JOIN jobs j ON j.id=a.id "
            "WHERE a.run_id=? ORDER BY a.created_at DESC,a.id", (run_id,),
        )]
        for audit in run["audits"]:
            audit["members"] = [dict(r) for r in conn.execute(
                "SELECT id,seed,status,error FROM runs WHERE audit_id=? ORDER BY created_at,rowid",
                (audit["id"],),
            )]
    run["config"] = decode_config(run.pop("config_json")) if run.get("config_json") else None
    for field in ("environment", "dataset", "validation"):
        run[field] = decode_snapshot(run.pop(field + "_json"), field) if run.get(field + "_json") else None
    run["evaluation"] = decode_snapshot(run.pop("evaluation_json"), "final_evaluation") if run.get("evaluation_json") else None
    run["progress"] = json.loads(run.pop("progress_json")) if run.get("progress_json") else None
    run["tracking"] = json.loads(run.pop("tracking_json")) if run.get("tracking_json") else None
    run["final_evaluation"] = decode_snapshot(run.pop("final_evaluation_json"), "final_evaluation") if run.get("final_evaluation_json") else None
    run["evaluation"] = run["final_evaluation"]
    run["tags"] = json.loads(run.pop("tags_json", "{}"))
    for decision in run["decisions"]:
        decision["details"] = decode_snapshot(decision.pop("details_json"), "decision_details") if decision.get("details_json") else None
        decision["evidence"] = decode_snapshot(decision.pop("evidence_json"), "decision_evidence") if decision.get("evidence_json") else None
    for audit in run["audits"]:
        audit["report"] = decode_snapshot(audit["report"], "audit_report") if audit["report"] else None
    run["run_id"] = run["id"]
    run["latest_decision"] = run["decisions"][0] if run["decisions"] else None
    run["best_val_accuracy"] = max((m["val_acc"] for m in run["metrics"]), default=None)
    run["total_duration_sec"] = sum(m["epoch_time_sec"] for m in run["metrics"])
    last = run["metrics"][-1] if run["metrics"] else None
    run["overfitting_gap"] = last["train_acc"] - last["val_acc"] if last else None
    return run


def comparison_page(exp_id, *, search="", architecture="", status="", seed=None,
                    accuracy_min=None, accuracy_max=None, dataset_name="", optimizer="",
                    architecture_depth=None, limit=50, offset=0):
    with database() as conn:
        experiment = conn.execute("SELECT * FROM experiments WHERE id=?", (exp_id,)).fetchone()
        if not experiment:
            return None, 0, []
        clauses = ["experiment_id=?", "audit_id IS NULL"]
        params = [exp_id]
        if search:
            clauses.append("(id LIKE ? OR approach_name LIKE ? OR model_architecture LIKE ? OR config_json LIKE ?)")
            like = f"%{search}%"
            params.extend([like] * 4)
        if dataset_name:
            clauses.append("COALESCE(json_extract(config_json,'$.dataset_name'),'cifar10')=?")
            params.append(dataset_name)
        if architecture:
            clauses.append("model_architecture=?")
            params.append(architecture)
        if optimizer:
            clauses.append("json_extract(config_json,'$.optimizer')=?")
            params.append(optimizer)
        if architecture_depth is not None:
            clauses.append("model_architecture='custom_cnn' AND json_extract(config_json,'$.architecture_config.depth')=?")
            params.append(architecture_depth)
        if status:
            clauses.append("(status=? OR (SELECT d.status FROM decisions d WHERE d.run_id=runs.id ORDER BY d.id DESC LIMIT 1)=?)")
            params.extend([status, status])
        if seed is not None:
            clauses.append("seed=?")
            params.append(seed)
        if accuracy_min is not None:
            clauses.append("CAST(json_extract(validation_json,'$.validation_accuracy') AS REAL)>=?")
            params.append(accuracy_min)
        if accuracy_max is not None:
            clauses.append("CAST(json_extract(validation_json,'$.validation_accuracy') AS REAL)<=?")
            params.append(accuracy_max)
        where = " AND ".join(clauses)
        total = conn.execute(f"SELECT count(*) FROM runs WHERE {where}", params).fetchone()[0]
        ids = [r[0] for r in conn.execute(
            f"SELECT id FROM runs WHERE {where} ORDER BY created_at DESC,id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )]
    return dict(experiment), total, ids


def search_exact_tag(tag_key=None, tag_value=None, *, search="", dataset_name="", architecture="",
                     status="", seed=None, accuracy_min=None, accuracy_max=None,
                     limit=50, offset=0):
    path = '$."' + tag_key + '"' if tag_key else None
    run_clauses = ["1=1"]
    run_params = []
    if path:
        run_clauses.append("json_extract(r.tags_json,?)=?")
        run_params.extend([path, tag_value])
    if search:
        run_clauses.append("(r.id LIKE ? OR r.approach_name LIKE ? OR r.config_json LIKE ?)")
        run_params.extend([f"%{search}%"] * 3)
    if dataset_name:
        run_clauses.append("COALESCE(json_extract(r.config_json,'$.dataset_name'),'cifar10')=?")
        run_params.append(dataset_name)
    if architecture:
        run_clauses.append("r.model_architecture=?")
        run_params.append(architecture)
    if status:
        run_clauses.append("(r.status=? OR (SELECT d.status FROM decisions d WHERE d.run_id=r.id ORDER BY d.id DESC LIMIT 1)=?)")
        run_params.extend([status, status])
    if seed is not None:
        run_clauses.append("r.seed=?")
        run_params.append(seed)
    if accuracy_min is not None or accuracy_max is not None:
        run_clauses.extend([
            "r.final_evaluation_status='COMPLETED'",
            "(SELECT d.status FROM decisions d WHERE d.run_id=r.id ORDER BY d.id DESC LIMIT 1)='SELECTED'",
            "COALESCE(json_extract(r.final_evaluation_json,'$.legacy_preselection_test_exposure'),0)=0",
        ])
    if accuracy_min is not None:
        run_clauses.append("CAST(json_extract(r.final_evaluation_json,'$.test_accuracy') AS REAL)>=?")
        run_params.append(accuracy_min)
    if accuracy_max is not None:
        run_clauses.append("CAST(json_extract(r.final_evaluation_json,'$.test_accuracy') AS REAL)<=?")
        run_params.append(accuracy_max)
    run_where = " AND ".join(run_clauses)
    exp_clauses, exp_params = ["1=1"], []
    if path:
        exp_clauses.append("json_extract(tags_json,?)=?")
        exp_params.extend([path, tag_value])
    if search:
        exp_clauses.append("(id LIKE ? OR name LIKE ? OR objective LIKE ?)")
        exp_params.extend([f"%{search}%"] * 3)
    exp_where = " AND ".join(exp_clauses)
    model_clauses, model_params = ["1=1"], []
    if path:
        model_clauses.append("json_extract(m.tags_json,?)=?")
        model_params.extend([path, tag_value])
    if search:
        model_clauses.append("(m.id LIKE ? OR m.name LIKE ? OR m.version LIKE ?)")
        model_params.extend([f"%{search}%"] * 3)
    if accuracy_min is not None:
        model_clauses.append("m.test_accuracy>=?")
        model_params.append(accuracy_min)
    if accuracy_max is not None:
        model_clauses.append("m.test_accuracy<=?")
        model_params.append(accuracy_max)
    related_clauses, related_params = [], []
    if dataset_name:
        related_clauses.append("COALESCE(json_extract(r.config_json,'$.dataset_name'),'cifar10')=?")
        related_params.append(dataset_name)
    if architecture:
        related_clauses.append("r.model_architecture=?")
        related_params.append(architecture)
    if status:
        related_clauses.append("(r.status=? OR (SELECT d.status FROM decisions d WHERE d.run_id=r.id ORDER BY d.id DESC LIMIT 1)=?)")
        related_params.extend([status, status])
    if seed is not None:
        related_clauses.append("r.seed=?")
        related_params.append(seed)
    if related_clauses:
        model_clauses.append(
            "EXISTS (SELECT 1 FROM runs r WHERE r.id=m.run_id AND "
            + " AND ".join(related_clauses) + ")"
        )
        model_params.extend(related_params)
    model_where = " AND ".join(model_clauses)
    with database() as conn:
        runs = [dict(r) for r in conn.execute(
            f"SELECT r.id,r.experiment_id,r.approach_name,r.status,r.seed,r.model_architecture,r.created_at "
            f"FROM runs r WHERE {run_where} ORDER BY r.created_at DESC,r.id LIMIT ? OFFSET ?",
            (*run_params, limit, offset),
        )]
        experiments = [dict(r) for r in conn.execute(
            f"SELECT id,name,created_at FROM experiments WHERE {exp_where} "
            "ORDER BY created_at DESC,id LIMIT ? OFFSET ?", (*exp_params, limit, offset),
        )]
        models = [dict(r) for r in conn.execute(
            f"SELECT m.id,m.name,m.version,m.run_id,m.status,m.test_accuracy,m.created_at FROM models m WHERE {model_where} "
            "ORDER BY m.created_at DESC,m.id LIMIT ? OFFSET ?", (*model_params, limit, offset),
        )]
    return {"tag": {"key": tag_key, "value": tag_value} if tag_key else None,
            "runs": runs,
            "experiments": experiments, "models": models, "limit": limit, "offset": offset}
