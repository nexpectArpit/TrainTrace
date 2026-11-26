"""Durable training orchestration; invoked only by the single worker."""

import json
import os
import random
import traceback
from pathlib import Path
import numpy as np
import torch
import torchvision
from config import DATA_DIR
from core.models import get_model_by_name
from core.dataset import (
    get_dataloaders,
    dataset_spec,
    preprocessing_contract,
)
from core.trainer import Trainer, TrainingStopped
from db.database import database
from storage import record_artifact, write_json, sha256, run_artifact_path, find_run_artifact
from snapshot_contracts import encode_snapshot
from reporting import render_dataset_preview
from tracking.provenance import checkpoint_state_sha256, environment
from tracking.external import WandbBridge
from tracking.metrics_export import initialize_metrics_csv, publish_metrics_csv
from tracking.dataset_preparation import load_training_data
from tracking.progress_recorder import TrainingProgressRecorder


def seed_everything(seed):
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def event(run_id, message):
    with database() as c:
        c.execute("INSERT INTO events(run_id,message) VALUES(?,?)", (run_id, str(message)))


def cancelled(job_id):
    with database() as c:
        row = c.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
        return bool(row and row[0])


def set_run(run_id, **fields):
    with database() as c:
        c.execute(
            "UPDATE runs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
            (*fields.values(), run_id),
        )


def execute_run(config, job_id):
    run_id = config["run_id"]
    wandb_bridge = None
    recorder = None

    def check():
        return cancelled(job_id)

    try:
        if check():
            raise TrainingStopped("Stopped before execution")
        seed_everything(config["seed"])
        env = environment()
        set_run(run_id, status="RUNNING", environment_json=encode_snapshot("environment", env))
        dataset_key, spec = dataset_spec(config.get("dataset_name", "cifar10"))
        set_run(
            run_id,
            progress_json=json.dumps(
                {
                    "phase": "model_setup",
                    "message": "Creating the selected model and loading initialization weights.",
                }
            ),
        )
        model = get_model_by_name(
            config["model_name"],
            num_classes=spec["num_classes"],
            pretrained=config["pretrained"],
            architecture_config=config.get("architecture_config"),
        )
        if config.get("initialize_from_run_id"):
            source_id = config["initialize_from_run_id"]
            checkpoint_kind = config["warm_start_checkpoint_kind"]
            checkpoint_path = find_run_artifact(
                source_id, f"{source_id}_{checkpoint_kind}.pt", "checkpoints"
            )
            if not checkpoint_path.is_file() or sha256(checkpoint_path) != config.get(
                "warm_start_checkpoint_sha256"
            ):
                raise ValueError("Warm-start checkpoint changed after run admission")
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
            if checkpoint.get("run_id") != source_id:
                raise ValueError("Warm-start checkpoint identity mismatch")
            model.load_state_dict(checkpoint["model_state_dict"], strict=True)
            event(
                run_id,
                f"Initialized model weights from run {source_id}; optimizer and scheduler start fresh.",
            )
        train, val, dataset_started = load_training_data(
            config,
            dataset_key,
            spec,
            set_run=set_run,
            event=event,
            loader=get_dataloaders,
        )
        event(
            run_id,
            f"{spec['name']} is ready: {len(train.dataset):,} training and {len(val.dataset):,} validation examples.",
        )
        set_run(
            run_id,
            progress_json=json.dumps(
                {
                    "phase": "model_setup",
                    "message": "Dataset ready; preparing model and training pipeline.",
                    "started_at": dataset_started,
                }
            ),
        )
        wandb_bridge = WandbBridge(config, run_id)
        set_run(run_id, tracking_json=json.dumps(wandb_bridge.metadata))
        if wandb_bridge.reason:
            event(run_id, wandb_bridge.reason + "; local training will continue.")
        base_dataset = getattr(train.dataset, "dataset", None)
        class_names = spec.get("classes") or getattr(base_dataset, "classes", None)
        if not class_names or len(class_names) != spec["num_classes"]:
            raise ValueError(f"{spec['name']} did not provide its expected class names")
        try:
            render_dataset_preview(run_id, base_dataset, class_names)
        except (OSError, ValueError, TypeError) as exc:
            event(run_id, f"Dataset preview unavailable: {exc}")
        # Store split index hash and dataset file hash, not merely a descriptive label.
        indexes = {"train": list(train.dataset.indices), "validation": list(val.dataset.indices)}
        split_path = write_json(run_id, "split", indexes)
        dataset = {
            "name": spec["name"],
            "dataset_name": dataset_key,
            "version": f"torchvision-{torchvision.__version__}",
            "num_classes": spec["num_classes"],
            "classes": list(class_names),
            "split_seed": config["split_seed"],
            "split_sha256": sha256(split_path),
            "split_ratios": {"train": 0.9, "validation": 0.1, "test": "official test partition"},
            "counts": {
                "train": len(train.dataset),
                "validation": len(val.dataset),
                "test": "official test partition (sealed until final evaluation)",
            },
            "preprocessing": _preprocessing_manifest(
                dataset_key, config["pretrained"], config["model_name"]
            ),
            "file_hashes": {
                str(p.relative_to(DATA_DIR)): sha256(p)
                for p in sorted((DATA_DIR / spec["source_dir"]).rglob("*"))
                if p.is_file()
            },
        }
        set_run(run_id, dataset_json=encode_snapshot("dataset", dataset))
        initialize_metrics_csv(run_id)
        trainer = Trainer(
            model,
            train,
            val,
            learning_rate=config["learning_rate"],
            scheduler_type=config["scheduler_type"],
            optimizer=config["optimizer"],
            weight_decay=config["weight_decay"],
            config=config,
            save_dir=run_artifact_path(
                run_id, f"{run_id}_best_checkpoint.pt", "checkpoints"
            ).parent,
        )

        recorder = TrainingProgressRecorder(run_id, trainer, check, set_run, wandb_bridge)

        history = trainer.train(
            config["epochs"],
            run_id,
            recorder.progress,
            lambda m: event(run_id, m),
            recorder.epoch,
            check,
            lambda kind, path: record_artifact(run_id, kind, path),
        )
        publish_metrics_csv(run_id)
        set_run(run_id, status="EVALUATING")
        event(
            run_id,
            "Finalizing validation evidence. The test partition remains sealed until selection.",
        )
        checkpoint = torch.load(
            history["best_checkpoint_path"], map_location=trainer.device, weights_only=True
        )
        best_epoch_index = max(range(len(history["val_acc"])), key=history["val_acc"].__getitem__)
        validation = {
            "metric_set": "validation",
            "validation_loss": history["val_loss"][best_epoch_index],
            "validation_accuracy": history["val_acc"][best_epoch_index],
            "checkpoint_sha256": sha256(history["best_checkpoint_path"]),
            "model_state_sha256": checkpoint_state_sha256(history["best_checkpoint_path"]),
            "checkpoint_epoch": checkpoint["epoch"],
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "model_size_bytes": Path(history["best_checkpoint_path"]).stat().st_size,
        }
        write_json(run_id, "validation", validation)
        set_run(
            run_id, status="COMPLETED", validation_json=encode_snapshot("validation", validation)
        )
        event(
            run_id, f"Completed: best validation accuracy {validation['validation_accuracy']:.2f}%"
        )
        return validation
    except TrainingStopped as e:
        publish_metrics_csv(run_id)
        set_run(run_id, status="STOPPED", error=str(e))
        event(run_id, str(e))
        raise
    except Exception:
        publish_metrics_csv(run_id)
        error = traceback.format_exc()
        set_run(run_id, status="FAILED", error=error)
        event(run_id, error)
        raise
    finally:
        if recorder:
            try:
                recorder.flush_samples()
            except Exception as exc:
                event(
                    run_id, f"Could not persist partial-epoch samples: {type(exc).__name__}: {exc}"
                )
        if wandb_bridge:
            wandb_bridge.close()


def _preprocessing_manifest(dataset_name, pretrained, model_name):
    contract = preprocessing_contract(dataset_name, pretrained, model_name)
    size = contract["size"][0]
    key = contract["dataset_name"]
    if key in {"cifar10", "cifar100"}:
        contract["augmentation"] = [f"RandomCrop({size},padding=4)", "RandomHorizontalFlip"]
    elif key in {"mnist", "fashion_mnist"}:
        contract["augmentation"] = ["RandomAffine(degrees=10,translate=0.08,scale=0.9-1.1,shear=5)"]
    elif key == "svhn":
        contract["augmentation"] = ["RandomAffine(degrees=5,translate=0.05,scale=0.95-1.05)"]
    else:
        contract["augmentation"] = []
    return contract
