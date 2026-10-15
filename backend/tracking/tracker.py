"""Durable training orchestration; invoked only by the single worker."""

import csv
import json
import os
import platform
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np
import torch
import torchvision
from config import DATA_DIR, ARTIFACTS_DIR, get_device_info, BASE_DIR
from core.models import get_model_by_name
from core.dataset import get_cifar10_dataloaders, CIFAR10_MEAN, CIFAR10_STD
from core.trainer import Trainer, TrainingStopped
from db.database import database
from storage import record_artifact, write_json, sha256, contained


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


def environment():
    def git(*args):
        try:
            return subprocess.check_output(
                ["git", "-C", str(BASE_DIR.parent), *args], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    # Hash source as well as commit: uncommitted code is part of the actual environment.
    source = {
        str(p.relative_to(BASE_DIR)): sha256(p)
        for p in sorted(BASE_DIR.rglob("*.py"))
        if "storage" not in p.parts and "tests" not in p.parts
    }
    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "device": get_device_info(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "source_hashes": source,
        "deterministic_algorithms": True,
        "torch_threads": torch.get_num_threads(),
    }


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

    def check():
        return cancelled(job_id)

    try:
        if check():
            raise TrainingStopped("Stopped before execution")
        seed_everything(config["seed"])
        env = environment()
        set_run(run_id, status="RUNNING", environment_json=json.dumps(env))
        event(
            run_id,
            "Loading CIFAR-10; cached data is reused. Split seed is independent of initialization seed.",
        )
        model = get_model_by_name(config["model_name"], pretrained=config["pretrained"])
        loaders = get_cifar10_dataloaders(
            batch_size=config["batch_size"],
            seed=config["seed"],
            split_seed=config["split_seed"],
            num_workers=0,
        )
        train, val, test = loaders
        # Store split index hash and dataset file hash, not merely a descriptive label.
        indexes = {"train": list(train.dataset.indices), "validation": list(val.dataset.indices)}
        split_path = write_json(run_id, "split", indexes)
        dataset = {
            "name": "CIFAR-10",
            "version": "torchvision-cifar10-python",
            "split_seed": config["split_seed"],
            "split_sha256": sha256(split_path),
            "counts": {
                "train": len(train.dataset),
                "validation": len(val.dataset),
                "test": len(test.dataset),
            },
            "preprocessing": {
                "size": [32, 32],
                "mean": CIFAR10_MEAN,
                "std": CIFAR10_STD,
                "augmentation": ["RandomCrop(32,padding=4)", "RandomHorizontalFlip"],
            },
            "file_hashes": {
                str(p.relative_to(DATA_DIR)): sha256(p)
                for p in sorted(DATA_DIR.rglob("data_batch_*"))
            },
        }
        set_run(run_id, dataset_json=json.dumps(dataset))
        trainer = Trainer(
            model,
            train,
            val,
            learning_rate=config["learning_rate"],
            scheduler_type=config["scheduler_type"],
            optimizer=config["optimizer"],
            weight_decay=config["weight_decay"],
            config=config,
        )

        def progress(**p):
            if check():
                raise TrainingStopped("Stopped by user")
            p["lr"] = trainer.optimizer.param_groups[0]["lr"]
            set_run(run_id, progress_json=json.dumps(p))

        def epoch(number, m):
            with database() as c:
                c.execute(
                    """INSERT INTO epoch_metrics(run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate)
                             VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        run_id,
                        number,
                        m["train_loss"],
                        m["train_acc"],
                        m["val_loss"],
                        m["val_acc"],
                        m["epoch_time_sec"],
                        m["learning_rate"],
                    ),
                )

        history = trainer.train(
            config["epochs"],
            run_id,
            progress,
            lambda m: event(run_id, m),
            epoch,
            check,
            lambda kind, path: record_artifact(run_id, kind, path),
        )
        set_run(run_id, status="EVALUATING")
        event(run_id, "Evaluating the best validation checkpoint on the holdout test set.")
        checkpoint = torch.load(
            history["best_checkpoint_path"], map_location=trainer.device, weights_only=True
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        evaluation = evaluate_candidate(model, test, trainer.device, check)
        evaluation.update(
            checkpoint_sha256=sha256(history["best_checkpoint_path"]),
            checkpoint_epoch=checkpoint["epoch"],
            parameter_count=sum(p.numel() for p in model.parameters()),
            model_size_bytes=Path(history["best_checkpoint_path"]).stat().st_size,
        )
        write_json(run_id, "evaluation", evaluation)
        with database() as c:
            metrics = [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM epoch_metrics WHERE run_id=? ORDER BY epoch", (run_id,)
                )
            ]
        path = contained(ARTIFACTS_DIR, f"{run_id}_metrics.csv")
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(metrics[0]))
            writer.writeheader()
            writer.writerows(metrics)
        record_artifact(run_id, "metrics_csv", path)
        set_run(run_id, status="COMPLETED", evaluation_json=json.dumps(evaluation))
        event(run_id, f"Completed: holdout accuracy {evaluation['test_accuracy']:.2f}%")
        return evaluation
    except TrainingStopped as e:
        set_run(run_id, status="STOPPED", error=str(e))
        event(run_id, str(e))
        raise
    except Exception:
        error = traceback.format_exc()
        set_run(run_id, status="FAILED", error=error)
        event(run_id, error)
        raise


def evaluate_candidate(model, loader, device, cancel=None):
    model.eval()
    matrix = torch.zeros(10, 10, dtype=torch.int64)
    loss_sum = count = 0
    if device.type == "cuda":
        torch.cuda.synchronize()
    if device.type == "mps":
        torch.mps.synchronize()
    start = time.perf_counter()
    with torch.inference_mode():
        for x, y in loader:
            if cancel and cancel():
                raise TrainingStopped("Stopped during holdout evaluation")
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss = torch.nn.functional.cross_entropy(out, y)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite holdout loss")
            count += len(y)
            loss_sum += loss.item() * len(y)
            values = (y * 10 + out.argmax(1)).cpu()
            matrix += torch.bincount(values, minlength=100).reshape(10, 10)
    if not count:
        raise ValueError("Empty holdout dataset")
    if device.type == "cuda":
        torch.cuda.synchronize()
    if device.type == "mps":
        torch.mps.synchronize()
    elapsed = time.perf_counter() - start
    tp = matrix.diag().double()
    precision = tp / matrix.sum(0).clamp(min=1)
    recall = tp / matrix.sum(1).clamp(min=1)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-15)
    return {
        "test_loss": loss_sum / count,
        "test_accuracy": 100 * tp.sum().item() / count,
        "precision_macro": precision.mean().item(),
        "recall_macro": recall.mean().item(),
        "f1_macro": f1.mean().item(),
        "confusion_matrix": matrix.tolist(),
        "latency_ms_per_sample": 1000 * elapsed / count,
        "latency_method": "Batched holdout wall time including loading/transfers, divided by sample count",
        "samples": count,
        "evaluation_seconds": elapsed,
    }
