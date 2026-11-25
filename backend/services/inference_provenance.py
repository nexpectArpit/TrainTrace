"""Validate recorded dataset metadata and locate verified run checkpoints."""

from fastapi import HTTPException

from config import ARTIFACTS_DIR
from storage import resolve_managed_path

MAX_COMPARE_RUNS = 6

def _locate_run_best_checkpoint(conn, run_id: str, expected_sha: str):
    artifact = conn.execute(
        "SELECT path, sha256 FROM artifacts WHERE run_id=? AND kind='best' ORDER BY id DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    try:
        if artifact:
            if artifact["sha256"] != expected_sha:
                return None
            path = resolve_managed_path(ARTIFACTS_DIR, artifact["path"])
        else:
            return None
    except ValueError:
        return None
    if not path.is_relative_to(ARTIFACTS_DIR.resolve()) or not path.is_file():
        return None
    return path


def _normalize_run_ids(raw_ids: list[str]) -> list[str]:
    cleaned = []
    for item in raw_ids:
        for part in str(item).split(","):
            value = part.strip()
            if value:
                cleaned.append(value)
    if not cleaned:
        raise HTTPException(422, "Select at least one completed run to compare")
    if len(cleaned) > MAX_COMPARE_RUNS:
        raise HTTPException(422, f"Select at most {MAX_COMPARE_RUNS} runs at a time")
    if len(set(cleaned)) != len(cleaned):
        raise HTTPException(422, "Duplicate run IDs are not allowed")
    for run_id in cleaned:
        if not all(c.isalnum() or c in "_-" for c in run_id):
            raise HTTPException(422, f"Invalid run ID: {run_id}")
    return cleaned


def require_inference_dataset(dataset: dict) -> tuple[str, str, list[str], int, dict]:
    """Return complete recorded metadata; never invent CIFAR labels or transforms."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset snapshot is missing")
    key = dataset.get("dataset_name")
    name = dataset.get("name")
    classes = dataset.get("classes")
    count = dataset.get("num_classes")
    preprocessing = dataset.get("preprocessing")
    if not isinstance(key, str) or not key.strip() or not isinstance(name, str) or not name.strip():
        raise ValueError("dataset identity is missing")
    if (not isinstance(classes, list) or not classes or
            not all(isinstance(label, str) and label.strip() for label in classes) or
            len(set(classes)) != len(classes) or
            type(count) is not int or count != len(classes)):
        raise ValueError("dataset class names or class count are missing or inconsistent")
    if not isinstance(preprocessing, dict):
        raise ValueError("preprocessing contract is missing")
    size = preprocessing.get("size")
    mean = preprocessing.get("mean")
    std = preprocessing.get("std")
    if (not isinstance(size, list) or len(size) != 2 or
            any(type(value) is not int or value <= 0 for value in size)):
        raise ValueError("preprocessing input size is missing or invalid")
    if (not isinstance(mean, list) or not isinstance(std, list) or
            len(mean) != 3 or len(std) != 3 or
            any(not isinstance(value, (int, float)) for value in mean + std) or
            any(value <= 0 for value in std)):
        raise ValueError("preprocessing normalization is missing or invalid")
    if preprocessing.get("input_conversion") not in {"rgb", "grayscale_to_rgb"}:
        raise ValueError("preprocessing input conversion is missing or invalid")
    if preprocessing.get("external_input_adapter") not in {"digit_photo_ink_v2", "aspect_fit_mean_pad"}:
        raise ValueError("preprocessing upload adapter is missing or unsupported")
    return key, name, classes, count, preprocessing
