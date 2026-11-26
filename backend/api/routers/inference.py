"""Serving predictions for the active registered version and side-by-side completed-run comparison."""

import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from config import REGISTRY_DIR, get_default_device
from db.database import database
from snapshot_contracts import decode_config, decode_snapshot
from storage import sha256, resolve_managed_path

from services.inference_runtime import _decode_uploaded_image, _predict_with_checkpoint
from services.inference_provenance import (
    _locate_run_best_checkpoint,
    _normalize_run_ids,
    require_inference_dataset,
)

router = APIRouter(prefix="/api/v1/inference", tags=["Inference"])


@router.get("/candidates")
def list_inference_candidates(experiment_id: str | None = Query(None, max_length=128)):
    """List completed runs with verified best checkpoints for ad-hoc side-by-side comparison."""
    clauses = [
        "r.status='COMPLETED'",
        "r.audit_id IS NULL",
        "r.config_json IS NOT NULL",
        "r.dataset_json IS NOT NULL",
        "r.validation_json IS NOT NULL",
    ]
    params = []
    if experiment_id:
        clauses.append("r.experiment_id=?")
        params.append(experiment_id)
    query = (
        "SELECT r.id, r.experiment_id, e.name AS experiment_name, r.approach_name, "
        "r.model_architecture, r.config_json, r.dataset_json, r.validation_json, r.created_at "
        "FROM runs r JOIN experiments e ON e.id=r.experiment_id "
        "WHERE " + " AND ".join(clauses) + " ORDER BY r.created_at DESC, r.id"
    )
    candidates = []
    with database() as conn:
        rows = conn.execute(query, params).fetchall()
        for row in rows:
            try:
                config = decode_config(row["config_json"])
                dataset = decode_snapshot(row["dataset_json"], "dataset")
                validation = decode_snapshot(row["validation_json"], "validation")
            except (ValueError, json.JSONDecodeError):
                continue
            expected_sha = (validation or {}).get("checkpoint_sha256")
            try:
                dataset_key, dataset_name, class_names, num_classes, preprocessing = (
                    require_inference_dataset(dataset)
                )
            except ValueError:
                continue
            if not expected_sha:
                continue
            path = _locate_run_best_checkpoint(conn, row["id"], expected_sha)
            if not path or sha256(path) != expected_sha:
                continue
            candidates.append(
                {
                    "run_id": row["id"],
                    "experiment_id": row["experiment_id"],
                    "experiment_name": row["experiment_name"],
                    "approach_name": row["approach_name"],
                    "model_architecture": row["model_architecture"],
                    "dataset_key": dataset_key,
                    "dataset_name": dataset_name,
                    "classes": list(class_names),
                    "num_classes": num_classes,
                    "input_size": preprocessing["size"],
                    "input_conversion": preprocessing["input_conversion"],
                    "validation_accuracy": validation.get("validation_accuracy"),
                    "checkpoint_epoch": validation.get("checkpoint_epoch"),
                    "checkpoint_sha256": expected_sha,
                    "pretrained": bool(config.get("pretrained")),
                    "created_at": row["created_at"],
                }
            )
    return {"candidates": candidates}


@router.post("/compare-runs")
def compare_completed_runs(
    file: UploadFile = File(...),
    run_ids: list[str] = Form(...),
    expected_label: str | None = Form(None),
):
    """Run one uploaded image through multiple verified completed-run checkpoints side by side."""
    normalized_ids = _normalize_run_ids(run_ids)
    image = _decode_uploaded_image(file)
    expected_clean = expected_label.strip() if expected_label and expected_label.strip() else None

    prepared = []
    with database() as conn:
        for run_id in normalized_ids:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                raise HTTPException(404, f"Run '{run_id}' not found")
            if (
                row["status"] != "COMPLETED"
                or not row["config_json"]
                or not row["dataset_json"]
                or not row["validation_json"]
            ):
                raise HTTPException(
                    409,
                    f"Run '{run_id}' must be a completed run with verified provenance",
                )
            try:
                configuration = decode_config(row["config_json"])
                dataset = decode_snapshot(row["dataset_json"], "dataset")
                validation = decode_snapshot(row["validation_json"], "validation")
            except (ValueError, json.JSONDecodeError) as e:
                raise HTTPException(409, f"Run '{run_id}' has unreadable provenance") from e
            if (
                not isinstance(configuration.get("model_name"), str)
                or not configuration["model_name"]
            ):
                raise HTTPException(
                    409, f"Run '{run_id}' is missing its recorded model architecture"
                )
            expected_sha = validation.get("checkpoint_sha256")
            try:
                dataset_key, dataset_name, class_names, num_classes, preprocessing = (
                    require_inference_dataset(dataset)
                )
            except ValueError as exc:
                raise HTTPException(
                    409, f"Run '{run_id}' has invalid dataset provenance: {exc}"
                ) from exc
            if not expected_sha:
                raise HTTPException(409, f"Run '{run_id}' is missing checkpoint integrity metadata")
            path = _locate_run_best_checkpoint(conn, run_id, expected_sha)
            if not path or sha256(path) != expected_sha:
                raise HTTPException(
                    409, f"Verified checkpoint for run '{run_id}' is missing or modified"
                )
            prepared.append(
                {
                    "row": dict(row),
                    "configuration": configuration,
                    "dataset": dataset,
                    "dataset_key": dataset_key,
                    "dataset_name": dataset_name,
                    "validation": validation,
                    "preprocessing": {**preprocessing, "dataset_name": dataset_key},
                    "class_names": class_names,
                    "num_classes": num_classes,
                    "path": path,
                    "sha256": expected_sha,
                }
            )

    if expected_clean is not None:
        any_match = any(
            expected_clean.lower() in {label.lower() for label in item["class_names"]}
            for item in prepared
        )
        if not any_match:
            raise HTTPException(
                422,
                f"Expected label '{expected_clean}' does not match any class in the selected runs' dataset(s)",
            )

    device = get_default_device()
    results = []
    for item in prepared:
        row = item["row"]
        configuration = item["configuration"]
        dataset = item["dataset"]
        validation = item["validation"]
        class_names = item["class_names"]
        num_classes = item["num_classes"]
        architecture = configuration["model_name"]
        probs, latency, order, input_preview = _predict_with_checkpoint(
            cache_key=("run", row["id"], item["sha256"], str(device)),
            architecture=architecture,
            num_classes=num_classes,
            configuration=configuration,
            preprocessing=item["preprocessing"],
            path=item["path"],
            expected_run_id=row["id"],
            image=image,
            device=device,
        )
        predicted_class = class_names[order[0]]
        expected_entry = {
            "expected_label": expected_clean,
            "expected_label_valid": None,
            "is_correct": None,
            "expected_class_confidence": None,
            "expected_class_rank": None,
        }
        if expected_clean is not None:
            lookup = {label.lower(): idx for idx, label in enumerate(class_names)}
            expected_idx = lookup.get(expected_clean.lower())
            if expected_idx is not None:
                canonical = class_names[expected_idx]
                expected_entry = {
                    "expected_label": canonical,
                    "expected_label_valid": True,
                    "is_correct": predicted_class == canonical,
                    "expected_class_confidence": probs[expected_idx],
                    "expected_class_rank": order.index(expected_idx) + 1,
                }
            else:
                expected_entry["expected_label_valid"] = False
        results.append(
            {
                "run_id": row["id"],
                "experiment_id": row["experiment_id"],
                "approach_name": row["approach_name"],
                "model_name": architecture,
                "dataset_name": item["dataset_name"],
                "dataset_key": item["dataset_key"],
                "checkpoint_kind": "best",
                "checkpoint_epoch": validation.get("checkpoint_epoch"),
                "checkpoint_sha256": item["sha256"],
                "validation_accuracy": validation.get("validation_accuracy"),
                "predicted_class": predicted_class,
                "confidence_score": probs[order[0]],
                "latency_ms": latency,
                "preprocessed_input_preview": input_preview,
                "preprocessing_size": item["preprocessing"]["size"],
                "all_probabilities": dict(zip(class_names, probs)),
                "top_k": [{"class": class_names[i], "confidence": probs[i]} for i in order[:3]],
                **expected_entry,
            }
        )

    dataset_names = sorted({r["dataset_name"] for r in results})
    same_dataset = len(dataset_names) == 1
    agreement = (
        len({r["predicted_class"] for r in results}) == 1
        if len(results) > 1 and same_dataset
        else None
    )
    evaluable = [r for r in results if r["is_correct"] is not None]
    correct_count = sum(1 for r in evaluable if r["is_correct"]) if expected_clean else None
    return {
        "mode": "completed_run_checkpoint_comparison",
        "note": (
            "Single-image comparison reports each checkpoint's prediction, confidence, and optional "
            "ground-truth match — not a dataset accuracy rate. Final-test selection rules remain unchanged."
        ),
        "expected_label": expected_clean,
        "models_compared": len(results),
        "datasets": dataset_names,
        "same_dataset": same_dataset,
        "agreement": agreement,
        "correct_count": correct_count,
        "evaluable_count": len(evaluable),
        "results": results,
    }


@router.post("/predict")
def predict_image(file: UploadFile = File(...), model_id: str | None = None):
    with database() as c:
        active = c.execute("SELECT model_id FROM serving WHERE id=1").fetchone()
        if not active:
            raise HTTPException(409, "Activate a registered model version first")
        if model_id and model_id != active[0]:
            raise HTTPException(409, "Requested version is not the active serving model")
        row = c.execute("SELECT * FROM models WHERE id=?", (active[0],)).fetchone()
    if not row or not row["manifest_json"] or not row["sha256"]:
        raise HTTPException(409, "Serving version has no verified provenance")
    model = dict(row)
    try:
        path = resolve_managed_path(REGISTRY_DIR, model["checkpoint_path"])
    except ValueError:
        raise HTTPException(409, "Registered checkpoint path is outside managed storage") from None
    if (
        not path.is_relative_to(REGISTRY_DIR.resolve())
        or not path.is_file()
        or sha256(path) != model["sha256"]
    ):
        raise HTTPException(409, "Serving checkpoint missing or changed")
    image = _decode_uploaded_image(file)
    try:
        manifest = json.loads(model["manifest_json"])
        configuration = manifest["configuration"]
        architecture = configuration["model_name"]
        dataset = manifest["dataset"]
        if not isinstance(architecture, str) or not architecture:
            raise ValueError("model architecture is missing")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, f"Registered model manifest is invalid: {exc}") from exc
    try:
        dataset_key, dataset_name, class_names, num_classes, preprocessing = (
            require_inference_dataset(dataset)
        )
    except ValueError as exc:
        raise HTTPException(409, f"Registered dataset provenance is invalid: {exc}") from exc
    device = get_default_device()
    probs, latency, order, input_preview = _predict_with_checkpoint(
        cache_key=("registry", model["id"], model["sha256"], str(device)),
        architecture=architecture,
        num_classes=num_classes,
        configuration=configuration,
        preprocessing={**preprocessing, "dataset_name": dataset_key},
        path=path,
        expected_run_id=model["run_id"],
        image=image,
        device=device,
    )
    return {
        "model_id": model["id"],
        "version": model["version"],
        "run_id": model["run_id"],
        "checkpoint_sha256": model["sha256"],
        "model_name": architecture,
        "dataset_name": dataset_name,
        "predicted_class": class_names[order[0]],
        "confidence_score": probs[order[0]],
        "latency_ms": latency,
        "preprocessed_input_preview": input_preview,
        "preprocessing_size": preprocessing["size"],
        "all_probabilities": dict(zip(class_names, probs)),
        "top_k": [{"class": class_names[i], "confidence": probs[i]} for i in order[:3]],
    }
