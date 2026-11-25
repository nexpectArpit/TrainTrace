"""Immutable registry versions with frozen scientific provenance."""

import json
import os
import shutil
from uuid import uuid4
from config import REGISTRY_DIR
from db.database import database
from storage import contained, sha256, resolve_managed_path, find_run_artifact
from snapshot_contracts import decode_config, decode_snapshot, encode_snapshot


class ModelRegistry:
    def promote_candidate(self, name, run_id, version="v1.0.0", tags=None):
        # Validate even when called outside HTTP.
        from domain import RegisterModel

        request = RegisterModel(name=name, run_id=run_id, version=version, tags=tags or {})
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
                if (
                    not run
                    or run["status"] != "COMPLETED"
                    or not run["validation_json"]
                    or not run["final_evaluation_json"]
                    or run["final_evaluation_status"] != "COMPLETED"
                ):
                    raise ValueError(
                        "A selected run with completed final test evaluation is required"
                    )
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
                source = find_run_artifact(run_id, f"{run_id}_best_checkpoint.pt", "checkpoints")
                evaluation = decode_snapshot(run["final_evaluation_json"], "final_evaluation")
                validation = decode_snapshot(run["validation_json"], "validation")
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
                    "manifest_schema_version": 1,
                    "source_experiment": exp,
                    "originating_run": dict(run),
                    "decision": dict(decision),
                    "investigation_history": investigation,
                    "evaluation": evaluation,
                    "validation": validation,
                    "checkpoint_sha256": digest,
                    "environment": decode_snapshot(run["environment_json"], "environment"),
                    "dataset": decode_snapshot(run["dataset_json"], "dataset"),
                    "configuration": decode_config(run["config_json"]),
                    "tags": request.tags,
                }
                c.execute(
                    "INSERT INTO models(id,name,version,run_id,checkpoint_path,test_accuracy,latency_ms,status,manifest_json,sha256,tags_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        model_id,
                        name,
                        version,
                        run_id,
                        target.relative_to(REGISTRY_DIR.resolve()).as_posix(),
                        evaluation["test_accuracy"],
                        evaluation.get("model_only_latency_ms_p50"),
                        "REGISTERED",
                        encode_snapshot("model_manifest", manifest),
                        digest,
                        json.dumps(request.tags),
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
            **decode_snapshot(model["manifest_json"], "model_manifest"),
        }

    def activate(self, model_id):
        model = self.get_model(model_id)
        try:
            path = resolve_managed_path(REGISTRY_DIR, model["checkpoint_path"])
        except ValueError:
            raise ValueError("Registered checkpoint path is outside managed storage") from None
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

        manifest = decode_snapshot(model["manifest_json"], "model_manifest")
        configuration = manifest["configuration"]
        num_classes = manifest.get("dataset", {}).get("num_classes", 10)
        net = get_model_by_name(
            configuration["model_name"],
            num_classes=num_classes,
            native_stem=bool(configuration.get("pretrained")),
            architecture_config=configuration.get("architecture_config"),
        )
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
