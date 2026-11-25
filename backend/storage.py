"""Managed, checksummed artifacts; callers never supply filesystem paths."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from config import ARTIFACTS_DIR
from db.database import database


def run_artifact_path(run_id, filename, category, *, create=True):
    """Locate a new run artifact under its run and evidence category."""
    if not run_id or not all(c.isalnum() or c in "_-" for c in run_id):
        raise ValueError("Invalid run ID")
    if category not in {"checkpoints", "metrics", "reports", "images", "data"}:
        raise ValueError("Invalid artifact category")
    if Path(filename).name != filename or not filename.startswith(run_id + "_"):
        raise ValueError("Invalid run artifact filename")
    directory = contained(ARTIFACTS_DIR, f"runs/{run_id}/{category}")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return contained(directory, filename)


def find_run_artifact(run_id, filename, category):
    """Read a structured artifact, falling back to the old flat layout."""
    path = run_artifact_path(run_id, filename, category, create=False)
    if path.is_file():
        return path
    return contained(ARTIFACTS_DIR, filename)


def contained(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Artifact path escapes managed storage.")
    return path


def resolve_managed_path(root, key):
    """Resolve a storage-relative key, while accepting safe absolute legacy paths."""
    root = Path(root).resolve()
    candidate = Path(key)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Managed storage key escapes its storage root.")
    return path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def record_artifact(run_id, kind, path):
    path = Path(path).resolve()
    if not path.is_relative_to(ARTIFACTS_DIR.resolve()):
        raise ValueError("Unmanaged artifact")
    digest = sha256(path)
    with database() as c:
        c.execute(
            """INSERT INTO artifacts(id,run_id,kind,path,sha256,size_bytes) VALUES(?,?,?,?,?,?)
          ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,size_bytes=excluded.size_bytes""",
            (
                uuid4().hex,
                run_id,
                kind,
                path.relative_to(ARTIFACTS_DIR.resolve()).as_posix(),
                digest,
                path.stat().st_size,
            ),
        )
    return digest


def readable_json(kind, payload):
    """Keep confusion-matrix rows together in the human-readable evaluation file."""
    if kind != "final_evaluation" or "confusion_matrix" not in payload:
        return json.dumps(payload, indent=2, allow_nan=False)
    fields = []
    for key, value in payload.items():
        if key == "confusion_matrix":
            rows = ["    " + json.dumps(row, allow_nan=False) for row in value]
            rendered = "[\n" + ",\n".join(rows) + "\n  ]" if rows else "[]"
        else:
            rendered = json.dumps(value, indent=2, allow_nan=False).replace("\n", "\n  ")
        fields.append(f"  {json.dumps(key)}: {rendered}")
    return "{\n" + ",\n".join(fields) + "\n}"


def write_json(run_id, kind, payload):
    if kind in {"validation", "final_evaluation"}:
        from snapshot_contracts import encode_snapshot

        payload = json.loads(encode_snapshot(kind, payload))
    category = "data" if kind == "split" else "reports"
    path = run_artifact_path(run_id, f"{run_id}_{kind}.json", category)
    temp = path.with_suffix(".tmp")
    temp.write_text(readable_json(kind, payload))
    os.replace(temp, path)
    record_artifact(run_id, kind, path)
    return path
