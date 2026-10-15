"""Managed, checksummed artifacts; callers never supply filesystem paths."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from config import ARTIFACTS_DIR
from db.database import database


def contained(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Artifact path escapes managed storage.")
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
            (uuid4().hex, run_id, kind, str(path), digest, path.stat().st_size),
        )
    return digest


def write_json(run_id, kind, payload):
    path = contained(ARTIFACTS_DIR, f"{run_id}_{kind}.json")
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False))
    os.replace(temp, path)
    record_artifact(run_id, kind, path)
    return path
