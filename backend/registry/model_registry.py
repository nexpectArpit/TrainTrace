"""Immutable registry versions with frozen scientific provenance."""

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4
from config import ARTIFACTS_DIR, REGISTRY_DIR
from db.database import database
from storage import contained, sha256


class ModelRegistry:
    def promote_candidate(self, name, run_id, version="v1.0.0"):
        # Validate even when called outside HTTP.
        from domain import RegisterModel

        request = RegisterModel(name=name, run_id=run_id, version=version)
        version = "v" + request.version.lstrip("v")
        target = None
        try:
            with database() as c:
                c.execute("BEGIN IMMEDIATE")
                if c.execute(
                    "SELECT 1 FROM models WHERE name=? AND version IN (?,?)",
                    (name, version, version[1:]),
                ).fetchone():
                    raise ValueError("Model name/version already exists; versions are immutable")
                run = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
                if not run or run["status"] != "COMPLETED" or not run["evaluation_json"]:
                    raise ValueError("A completed, holdout-evaluated run is required")
                decision = c.execute(
                    "SELECT * FROM decisions WHERE run_id=? ORDER BY id DESC LIMIT 1", (run_id,)
                ).fetchone()
                if (
                    not decision
                    or decision["status"] != "SELECTED"
                    or not decision["evidence_json"]
                ):
                    raise ValueError("Record an evidence-backed Selected decision first")
                if not all(run[k] for k in ["config_json", "environment_json", "dataset_json"]):
                    raise ValueError(
                        "Historical provenance is unknown. Re-run this legacy candidate."
                    )
                source = contained(ARTIFACTS_DIR, f"{run_id}_best_checkpoint.pt")
                evaluation = json.loads(run["evaluation_json"])
                if not source.is_file() or sha256(source) != evaluation["checkpoint_sha256"]:
                    raise ValueError("Evaluated checkpoint missing or modified")
                exp = dict(
                    c.execute(
                        "SELECT * FROM experiments WHERE id=?", (run["experiment_id"],)
                    ).fetchone()
                )
                investigation = []
                for row in c.execute(
                    "SELECT * FROM runs WHERE experiment_id=? AND audit_id IS NULL ORDER BY created_at,id",
                    (run["experiment_id"],),
                ).fetchall():
                    r = dict(row)
                    r["decisions"] = [
                        dict(d)
                        for d in c.execute(
                            "SELECT * FROM decisions WHERE run_id=? ORDER BY id", (r["id"],)
                        )
                    ]
                    investigation.append(r)
                model_id = "model_" + uuid4().hex
                target = contained(REGISTRY_DIR, model_id + ".pt")
                temp = target.with_suffix(".tmp")
                try:
                    shutil.copyfile(source, temp)
                    digest = sha256(temp)
                    if digest != evaluation["checkpoint_sha256"]:
                        raise ValueError("Checkpoint changed during registration")
                    os.replace(temp, target)
                finally:
                    temp.unlink(missing_ok=True)
                manifest = {
                    "source_experiment": exp,
                    "originating_run": dict(run),
                    "decision": dict(decision),
                    "investigation_history": investigation,
                    "evaluation": evaluation,
                    "checkpoint_sha256": digest,
                    "environment": json.loads(run["environment_json"]),
                    "dataset": json.loads(run["dataset_json"]),
                    "configuration": json.loads(run["config_json"]),
                }
                c.execute(
                    "INSERT INTO models(id,name,version,run_id,checkpoint_path,test_accuracy,latency_ms,status,manifest_json,sha256) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        model_id,
                        name,
                        version,
                        run_id,
                        str(target),
                        evaluation["test_accuracy"],
                        evaluation["latency_ms_per_sample"],
                        "REGISTERED",
                        json.dumps(manifest),
                        digest,
                    ),
                )
            return self.get_model(model_id)
        except BaseException:
            if target:
                target.unlink(missing_ok=True)
            raise

    def get_model(self, model_id):
        with database() as c:
            row = c.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
        if not row:
            raise ValueError("Model version not found")
        return dict(row)

    def get_lineage(self, model_id):
        model = self.get_model(model_id)
        if not model["manifest_json"]:
            return {
                "model": model,
                "verified": False,
                "reason": "Legacy version has no frozen provenance snapshot.",
            }
        return {
            "model": {k: v for k, v in model.items() if k != "manifest_json"},
            "verified": True,
            **json.loads(model["manifest_json"]),
        }

    def activate(self, model_id):
        model = self.get_model(model_id)
        path = Path(model["checkpoint_path"]).resolve()
        if (
            not model["manifest_json"]
            or not model["sha256"]
            or not path.is_relative_to(REGISTRY_DIR.resolve())
            or not path.is_file()
            or sha256(path) != model["sha256"]
        ):
            raise ValueError("Only an intact, verified registered version can serve predictions")
        # Validate architecture and state before making it the active version.
        import torch
        from core.models import get_model_by_name

        manifest = json.loads(model["manifest_json"])
        net = get_model_by_name(manifest["configuration"]["model_name"])
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        if checkpoint["run_id"] != model["run_id"]:
            raise ValueError("Checkpoint run identity mismatch")
        net.load_state_dict(checkpoint["model_state_dict"])
        with database() as c:
            c.execute(
                "INSERT INTO serving(id,model_id) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET model_id=excluded.model_id",
                (model_id,),
            )
        return {"model_id": model_id, "status": "ACTIVE"}
