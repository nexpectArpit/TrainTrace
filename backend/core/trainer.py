"""Explicit PyTorch training with epoch durability and atomic checkpoints."""

import math
import os
import random
import shutil
import time
import sys

try:
    import resource
except ImportError:
    resource = None
from pathlib import Path
import numpy as np
import torch
from config import ARTIFACTS_DIR, get_default_device
from storage import contained


class TrainingStopped(Exception):
    pass


def train_one_epoch(
    model,
    dataloader,
    criterion,
    optimizer,
    device,
    epoch=1,
    total_epochs=1,
    progress_callback=None,
    cancel=None,
):
    model.train()
    started = time.perf_counter()
    cpu_started = time.process_time()
    loss_sum = correct = count = 0
    for index, (x, y) in enumerate(dataloader):
        if cancel and cancel():
            raise TrainingStopped("Stopped by user")
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        if not torch.isfinite(loss):
            raise ValueError("Non-finite training loss")
        loss.backward()
        optimizer.step()
        count += len(y)
        loss_sum += loss.item() * len(y)
        correct += (logits.argmax(1) == y).sum().item()
        if progress_callback and (index % 25 == 0 or index + 1 == len(dataloader)):
            elapsed = max(time.perf_counter() - started, 1e-9)
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
            progress_callback(
                epoch=epoch,
                total_epochs=total_epochs,
                batch_idx=index + 1,
                total_batches=len(dataloader),
                batch_loss=loss.item(),
                running_acc=100 * correct / count,
                samples_per_sec=count / elapsed,
                worker_cpu_percent=100 * (time.process_time() - cpu_started) / elapsed,
                peak_rss_mb=(
                    peak_rss / (1024 * 1024) if sys.platform == "darwin" else peak_rss / 1024
                )
                if peak_rss is not None
                else None,
            )
    if not count:
        raise ValueError("Empty training dataset")
    return loss_sum / count, 100 * correct / count


def evaluate(model, dataloader, criterion, device, cancel=None):
    model.eval()
    loss_sum = correct = count = 0
    with torch.inference_mode():
        for x, y in dataloader:
            if cancel and cancel():
                raise TrainingStopped("Stopped by user")
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite evaluation loss")
            count += len(y)
            loss_sum += loss.item() * len(y)
            correct += (logits.argmax(1) == y).sum().item()
    if not count:
        raise ValueError("Empty evaluation dataset")
    return loss_sum / count, 100 * correct / count


class Trainer:
    def __init__(
        self,
        model,
        train_loader,
        val_loader,
        learning_rate=0.001,
        scheduler_type="constant",
        device=None,
        save_dir=None,
        optimizer="adamw",
        weight_decay=0.0001,
        config=None,
    ):
        self.device = device or get_default_device()
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.save_dir = Path(save_dir or ARTIFACTS_DIR)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.criterion = torch.nn.CrossEntropyLoss()
        self.config = config or {}
        if optimizer not in ["adamw", "sgd"]:
            raise ValueError("Unsupported optimizer")
        factory = torch.optim.AdamW if optimizer == "adamw" else torch.optim.SGD
        options = {"momentum": 0.9} if optimizer == "sgd" else {}
        self.optimizer = factory(
            model.parameters(), lr=learning_rate, weight_decay=weight_decay, **options
        )
        self.scheduler_type = scheduler_type
        self.scheduler = None

    def train(
        self,
        num_epochs,
        run_id="run_default",
        progress_callback=None,
        log_callback=None,
        epoch_callback=None,
        cancel=None,
        artifact_callback=None,
    ):
        if num_epochs < 1:
            raise ValueError("At least one epoch required")
        if self.scheduler_type == "cosine":
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=num_epochs
            )
        elif self.scheduler_type == "step":
            self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=2, gamma=0.5)
        elif self.scheduler_type != "constant":
            raise ValueError("Unsupported scheduler")
        history = {
            k: []
            for k in [
                "train_loss",
                "train_acc",
                "val_loss",
                "val_acc",
                "epoch_times",
                "learning_rates",
            ]
        }
        best = -math.inf
        best_path = None

        def checkpoint(kind, epoch, metrics):
            path = contained(self.save_dir, f"{run_id}_{kind}_checkpoint.pt")
            temp = path.with_suffix(".tmp")
            numpy_state = np.random.get_state()
            rng_state = {
                "python": random.getstate(),
                "numpy": {
                    "algorithm": numpy_state[0],
                    "keys": torch.from_numpy(numpy_state[1].copy()),
                    "position": int(numpy_state[2]),
                    "has_gauss": int(numpy_state[3]),
                    "cached_gaussian": float(numpy_state[4]),
                },
                "torch_cpu": torch.get_rng_state(),
                "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
                "train_loader_generator": (
                    self.train_loader.generator.get_state()
                    if getattr(self.train_loader, "generator", None) is not None
                    else None
                ),
            }
            torch.save(
                {
                    "epoch": epoch,
                    "run_id": run_id,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "scheduler_state_dict": self.scheduler.state_dict() if self.scheduler else None,
                    "rng_state": rng_state,
                    "config": self.config,
                    **metrics,
                },
                temp,
            )
            os.replace(temp, path)
            if artifact_callback:
                artifact_callback(kind, path)
            return str(path)

        for epoch in range(1, num_epochs + 1):
            if cancel and cancel():
                raise TrainingStopped("Stopped by user")
            start = time.perf_counter()
            lr = self.optimizer.param_groups[0]["lr"]
            tl, ta = train_one_epoch(
                self.model,
                self.train_loader,
                self.criterion,
                self.optimizer,
                self.device,
                epoch,
                num_epochs,
                progress_callback,
                cancel,
            )
            if progress_callback:
                progress_callback(
                    phase="validation",
                    epoch=epoch,
                    total_epochs=num_epochs,
                    batch_idx=0,
                    total_batches=0,
                )
            vl, va = evaluate(self.model, self.val_loader, self.criterion, self.device, cancel)
            metrics = {
                "train_loss": tl,
                "train_acc": ta,
                "val_loss": vl,
                "val_acc": va,
                "epoch_time_sec": time.perf_counter() - start,
                "learning_rate": lr,
            }
            for key in ["train_loss", "train_acc", "val_loss", "val_acc"]:
                history[key].append(metrics[key])
            history["epoch_times"].append(metrics["epoch_time_sec"])
            history["learning_rates"].append(lr)
            # Persist completed epochs before any subsequent epoch can fail.
            if epoch_callback:
                epoch_callback(epoch, metrics)
            if self.scheduler:
                self.scheduler.step()
            checkpoint("last", epoch, metrics)
            if va > best:
                best = va
                # Copy the already-serialised last checkpoint to best instead of
                # calling torch.save a second time (saves ~40–90 MB/epoch for
                # ResNet / EfficientNet without sacrificing any durability guarantee).
                last_path = contained(self.save_dir, f"{run_id}_last_checkpoint.pt")
                best_path_target = contained(self.save_dir, f"{run_id}_best_checkpoint.pt")
                best_temp = best_path_target.with_suffix(".tmp")
                shutil.copy2(str(last_path), str(best_temp))
                os.replace(best_temp, best_path_target)
                best_path = str(best_path_target)
                if artifact_callback:
                    artifact_callback("best", best_path_target)
            if epoch % 5 == 0:
                checkpoint(f"epoch_{epoch}", epoch, metrics)
            if log_callback:
                log_callback(
                    f"Epoch {epoch}/{num_epochs}: train {ta:.2f}%, validation {va:.2f}%, loss {vl:.4f}"
                )
        history.update(best_val_acc=best, best_checkpoint_path=best_path)
        return history
