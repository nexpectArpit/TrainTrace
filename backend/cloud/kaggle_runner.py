# ruff: noqa
"""Standalone Kaggle kernel template. Placeholders are filled by kaggle_bridge."""

import csv
import hashlib
import json
import os
import random
import subprocess
import time
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset, Dataset
from torchvision import datasets, transforms

CONFIG = json.loads(__TT_CONFIG_JSON__)
TRAINTRACE_SOURCE_HASHES = __TT_SOURCE_HASHES__
TRAINTRACE_GIT_COMMIT = __TT_GIT_COMMIT__
TRAINTRACE_GIT_DIRTY = __TT_GIT_DIRTY__
exec(compile(__TT_MODEL_SOURCE__, "traintrace/core/models.py", "exec"), globals())
exec(compile(__TT_DATASET_CONTRACT_SOURCE__, "traintrace/core/dataset_contract.py", "exec"), globals())

RUN_ID = CONFIG["run_id"]
CALLBACK_URL = (__TT_CALLBACK_URL__ or os.environ.get("TRAINTRACE_CALLBACK_URL", "")).rstrip("/")
OUTPUT_DIR = Path("/kaggle/working")
DATA_DIR = OUTPUT_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET_CATALOG = {
    key: {
        **spec,
        "class": getattr(datasets, spec["torchvision_name"]),
        "grayscale": bool(spec.get("grayscale")),
    }
    for key, spec in DATASET_SPECS.items()
}


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


def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    random.seed(worker_seed)
    np.random.seed(worker_seed)


def make_transforms(dataset_key, pretrained):
    spec = DATASET_CATALOG[dataset_key]
    contract = preprocessing_contract(dataset_key, pretrained, CONFIG["model_name"])
    size = contract["size"][0]
    mean = contract["mean"]
    std = contract["std"]
    prefix = [transforms.Grayscale(num_output_channels=3)] if spec["grayscale"] else []
    prefix.append(transforms.Resize((size, size)))
    train_ops = list(prefix)
    if dataset_key in {"cifar10", "cifar100"}:
        train_ops.extend([transforms.RandomCrop(size, padding=4), transforms.RandomHorizontalFlip(p=0.5)])
        augmentation = [f"RandomCrop({size},padding=4)", "RandomHorizontalFlip"]
    elif dataset_key in {"mnist", "fashion_mnist"}:
        train_ops.append(transforms.RandomAffine(degrees=10, translate=(0.08, 0.08), scale=(0.9, 1.1), shear=5, fill=0))
        augmentation = ["RandomAffine(degrees=10,translate=0.08,scale=0.9-1.1,shear=5)"]
    else:
        train_ops.append(transforms.RandomAffine(degrees=5, translate=(0.05, 0.05), scale=(0.95, 1.05), fill=0))
        augmentation = ["RandomAffine(degrees=5,translate=0.05,scale=0.95-1.05)"]
    train_ops.extend([transforms.ToTensor(), transforms.Normalize(mean, std)])
    eval_ops = prefix + [transforms.ToTensor(), transforms.Normalize(mean, std)]
    contract["augmentation"] = augmentation
    return transforms.Compose(train_ops), transforms.Compose(eval_ops), contract


def make_dataset(dataset_key, split, transform):
    dataset_class = DATASET_CATALOG[dataset_key]["class"]
    if dataset_key == "cifar10":
        # Official cs.toronto.edu often throttles cloud IPs (~59 kB/s);
        # try fast AWS S3 mirror first, falling back to torchvision default on error.
        original_url = getattr(dataset_class, "url", None)
        for candidate_url in (
            "https://air-example-data.s3.us-west-2.amazonaws.com/cifar-10-python.tar.gz",
            original_url,
        ):
            if not candidate_url:
                continue
            try:
                dataset_class.url = candidate_url
                return dataset_class(
                    root=str(DATA_DIR), train=(split == "train"), download=True, transform=transform
                )
            except Exception:
                if candidate_url == original_url:
                    raise
    if dataset_key == "svhn":
        return dataset_class(root=str(DATA_DIR), split=split, download=True, transform=transform)
    return dataset_class(root=str(DATA_DIR), train=(split == "train"), download=True, transform=transform)


class TransformView(Dataset):
    """Apply a view-specific transform while sharing one decoded base dataset."""
    def __init__(self, dataset, transform):
        self.dataset = dataset
        self.transform = transform
        self.classes = getattr(dataset, "classes", None)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        image, label = self.dataset[index]
        if self.transform is not None:
            image = self.transform(image)
        return image, label


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gpu_metrics(query_smi=True):
    values = {
        "gpu_utilization_pct": None,
        "gpu_memory_used_mb": None,
        "gpu_memory_total_mb": None,
        "gpu_memory_utilization_pct": None,
        "gpu_temperature_c": None,
        "gpu_power_watts": None,
    }
    if query_smi:
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
                text=True, stderr=subprocess.DEVNULL, timeout=2,
            ).splitlines()[0]
            fields = [field.strip() for field in output.split(",")]
            for name, value in zip(
                ("gpu_utilization_pct", "gpu_memory_used_mb", "gpu_memory_total_mb", "gpu_temperature_c", "gpu_power_watts"),
                fields,
            ):
                if value not in {"", "N/A", "[N/A]"}:
                    values[name] = float(value)
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
    if values["gpu_memory_used_mb"] is not None and values["gpu_memory_total_mb"]:
        values["gpu_memory_utilization_pct"] = (
            100.0 * values["gpu_memory_used_mb"] / values["gpu_memory_total_mb"]
        )
    if torch.cuda.is_available():
        values["device_memory_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
    else:
        values["device_memory_mb"] = 0.0
    try:
        import psutil
        proc = psutil.Process()
        values["worker_cpu_percent"] = proc.cpu_percent(interval=None)
        values["peak_rss_mb"] = proc.memory_info().rss / (1024 * 1024)
    except ImportError:
        values["worker_cpu_percent"] = None
        values["peak_rss_mb"] = None
    return values


def post_telemetry(path, payload):
    if not CALLBACK_URL:
        return
    try:
        request = urllib.request.Request(
            f"{CALLBACK_URL}/api/v1/runs/{RUN_ID}/{path}",
            data=json.dumps(payload, allow_nan=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=1.0).close()
    except Exception as exc:
        print(f"TrainTrace callback unavailable ({type(exc).__name__}); stdout telemetry remains enabled.", flush=True)


def evaluate(model, loader, criterion, device):
    model.eval()
    non_blocking = device.type == "cuda"
    loss_sum = correct = count = 0
    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device, non_blocking=non_blocking)
            labels = labels.to(device, non_blocking=non_blocking)
            logits = model(images)
            loss = criterion(logits, labels)
            count += labels.size(0)
            loss_sum += loss.item() * labels.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
    if count == 0:
        raise ValueError("Validation dataset is empty")
    return loss_sum / count, 100.0 * correct / count


def main():
    dataset_key, _ = dataset_spec(CONFIG["dataset_name"])
    spec = DATASET_CATALOG[dataset_key]
    seed_everything(int(CONFIG["seed"]))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAINTRACE_SYSTEM] device={device} gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}", flush=True)

    print(f"[TRAINTRACE_STAGE] {{\"phase\":\"dataset_preparation\",\"dataset\":{json.dumps(dataset_key)},\"message\":\"Downloading and verifying dataset partitions on Kaggle.\"}}", flush=True)
    train_transform, eval_transform, preprocessing = make_transforms(dataset_key, bool(CONFIG["pretrained"]))
    print("[TRAINTRACE_STAGE] " + json.dumps({"phase": "dataset_preparation", "message": f"Loading {spec['name']} train partition; download may take time on a cold Kaggle kernel."}), flush=True)
    # Download/load the train partition once and apply train/eval transforms via
    # lightweight views. Do not fetch the sealed test partition during training.
    raw_train = make_dataset(dataset_key, "train", None)
    train_full = TransformView(raw_train, train_transform)
    eval_full = TransformView(raw_train, eval_transform)
    print("[TRAINTRACE_STAGE] " + json.dumps({"phase": "dataset_preparation", "message": f"Training partition ready: {len(raw_train):,} images."}), flush=True)
    validation_count = int(len(train_full) * 0.1)
    train_count = len(train_full) - validation_count
    split_generator = torch.Generator().manual_seed(int(CONFIG["split_seed"]))
    train_subset, validation_subset = torch.utils.data.random_split(
        train_full, [train_count, validation_count], generator=split_generator
    )
    validation_data = Subset(eval_full, validation_subset.indices)
    print(f"[TRAINTRACE_STAGE] {{\"phase\":\"dataset_preparation\",\"dataset\":{json.dumps(dataset_key)},\"message\":\"Dataset downloaded; building deterministic train and validation loaders.\"}}", flush=True)
    train_generator = torch.Generator().manual_seed(int(CONFIG["seed"]))
    use_cuda = torch.cuda.is_available()
    train_loader = DataLoader(
        train_subset, batch_size=int(CONFIG["batch_size"]), shuffle=True,
        generator=train_generator, worker_init_fn=seed_worker,
        num_workers=2, pin_memory=use_cuda, persistent_workers=True,
    )
    validation_loader = DataLoader(
        validation_data, batch_size=int(CONFIG["batch_size"]), shuffle=False,
        num_workers=2, pin_memory=use_cuda, persistent_workers=True,
    )

    class_names = spec.get("classes") or getattr(train_full, "classes", None)
    if not class_names or len(class_names) != spec["num_classes"]:
        raise ValueError(f"{spec['name']} did not provide its expected class names")
    class_names = list(class_names)
    split = {"train": list(train_subset.indices), "validation": list(validation_subset.indices)}
    split_path = OUTPUT_DIR / f"{RUN_ID}_split.json"
    split_path.write_text(json.dumps(split, indent=2))
    split_sha256 = hash_file(split_path)
    source_root = DATA_DIR / spec["source_dir"]
    file_hashes = {
        path.relative_to(DATA_DIR).as_posix(): hash_file(path)
        for path in sorted(source_root.rglob("*")) if path.is_file()
    }
    dataset_snapshot = {
        "name": spec["name"], "dataset_name": dataset_key,
        "version": f"torchvision-{__import__('torchvision').__version__}",
        "num_classes": spec["num_classes"], "classes": class_names,
        "split_seed": int(CONFIG["split_seed"]), "split_sha256": split_sha256,
        "split_ratios": {"train": 0.9, "validation": 0.1, "test": "official test partition"},
        "counts": {"train": len(train_subset), "validation": len(validation_data), "test": "official test partition (sealed until final evaluation)"},
        "preprocessing": preprocessing, "file_hashes": file_hashes,
    }

    model = get_model_by_name(
        CONFIG["model_name"], num_classes=spec["num_classes"],
        pretrained=bool(CONFIG["pretrained"]),
        architecture_config=CONFIG.get("architecture_config"),
    ).to(device)
    print(f"[TRAINTRACE_STAGE] {{\"phase\":\"training\",\"message\":\"Model initialized; beginning monitored training.\"}}", flush=True)
    criterion = nn.CrossEntropyLoss()
    optimizer_name = CONFIG["optimizer"].lower()
    optimizer_factory = torch.optim.AdamW if optimizer_name == "adamw" else torch.optim.SGD
    optimizer_options = {"momentum": 0.9} if optimizer_name == "sgd" else {}
    optimizer = optimizer_factory(
        model.parameters(), lr=float(CONFIG["learning_rate"]),
        weight_decay=float(CONFIG["weight_decay"]), **optimizer_options,
    )
    scheduler_type = CONFIG["scheduler_type"]
    epochs = int(CONFIG["epochs"])
    if scheduler_type == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    elif scheduler_type == "step":
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
    elif scheduler_type == "constant":
        scheduler = None
    else:
        raise ValueError(f"Unsupported scheduler: {scheduler_type}")

    history = []
    progress = []
    best_val_accuracy = -1.0
    best_epoch = None
    best_path = OUTPUT_DIR / f"{RUN_ID}_best_checkpoint.pt"
    last_path = OUTPUT_DIR / f"{RUN_ID}_last_checkpoint.pt"
    total_start = time.perf_counter()
    print(f"Dataset ready: {len(train_subset):,} train / {len(validation_data):,} validation samples", flush=True)
    for epoch in range(1, epochs + 1):
        epoch_start = time.perf_counter()
        learning_rate = optimizer.param_groups[0]["lr"]
        model.train()
        count = correct = 0
        loss_sum = 0.0
        interval_count = 0
        interval_started = time.perf_counter()
        for batch_idx, (images, labels) in enumerate(train_loader, 1):
            images = images.to(device, non_blocking=use_cuda)
            labels = labels.to(device, non_blocking=use_cuda)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss")
            loss.backward()
            optimizer.step()
            batch_count = labels.size(0)
            count += batch_count
            interval_count += batch_count
            loss_sum += loss.item() * batch_count
            correct += (logits.argmax(1) == labels).sum().item()
            if batch_idx % 25 == 0 or batch_idx == len(train_loader):
                elapsed = max(time.perf_counter() - interval_started, 1e-9)
                sample = {
                    "epoch": epoch, "batch_idx": batch_idx,
                    "total_batches": len(train_loader), "batch_loss": float(loss.item()),
                    "running_acc": 100.0 * correct / max(count, 1),
                    "samples_per_sec": interval_count / elapsed,
                    "learning_rate": optimizer.param_groups[0]["lr"],
                    **gpu_metrics(query_smi=(batch_idx % 100 == 0 or batch_idx == len(train_loader))),
                }
                interval_count = 0
                interval_started = time.perf_counter()
                progress.append(sample)
                print("[TRAINTRACE_METRIC] " + json.dumps(sample, allow_nan=False), flush=True)
                post_telemetry("telemetry", sample)

        train_loss = loss_sum / max(count, 1)
        train_accuracy = 100.0 * correct / max(count, 1)
        val_loss, val_accuracy = evaluate(model, validation_loader, criterion, device)
        if scheduler is not None:
            scheduler.step()
        epoch_metrics = {
            "epoch": epoch, "train_loss": train_loss, "train_acc": train_accuracy,
            "val_loss": val_loss, "val_acc": val_accuracy,
            "epoch_time_sec": time.perf_counter() - epoch_start,
            "learning_rate": learning_rate,
        }
        history.append(epoch_metrics)
        print("[TRAINTRACE_EPOCH] " + json.dumps(epoch_metrics, allow_nan=False), flush=True)
        post_telemetry("epoch-telemetry", epoch_metrics)
        checkpoint = {
            "epoch": epoch, "run_id": RUN_ID, "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(), "config": CONFIG,
        }
        torch.save(checkpoint, last_path)
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_epoch = epoch
            torch.save(checkpoint, best_path)
        print(
            f"Epoch {epoch}/{epochs}: train loss={train_loss:.4f} acc={train_accuracy:.2f}% "
            f"val loss={val_loss:.4f} acc={val_accuracy:.2f}% time={epoch_metrics['epoch_time_sec']:.2f}s",
            flush=True,
        )

    metrics_path = OUTPUT_DIR / f"{RUN_ID}_metrics.csv"
    with metrics_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    progress_path = OUTPUT_DIR / f"{RUN_ID}_progress.csv"
    if progress:
        with progress_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(progress[0]))
            writer.writeheader()
            writer.writerows(progress)

    # Save readable visual artifacts alongside the same metrics used by the UI.
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot([row["epoch"] for row in history], [row["train_loss"] for row in history], marker="o", label="Train")
    axes[0].plot([row["epoch"] for row in history], [row["val_loss"] for row in history], marker="o", label="Validation")
    axes[0].set(title="Loss by epoch", xlabel="Epoch", ylabel="Cross-entropy"); axes[0].legend(); axes[0].grid(alpha=0.25)
    axes[1].plot([row["epoch"] for row in history], [row["train_acc"] for row in history], marker="o", label="Train")
    axes[1].plot([row["epoch"] for row in history], [row["val_acc"] for row in history], marker="o", label="Validation")
    axes[1].set(title="Accuracy by epoch", xlabel="Epoch", ylabel="Accuracy (%)"); axes[1].legend(); axes[1].grid(alpha=0.25)
    figure.tight_layout(); figure.savefig(OUTPUT_DIR / f"{RUN_ID}_training_curves.png", dpi=150); plt.close(figure)

    preview = eval_full
    figure, axes = plt.subplots(2, 5, figsize=(10, 5))
    mean_tensor = torch.tensor(preprocessing["mean"]).view(3, 1, 1)
    std_tensor = torch.tensor(preprocessing["std"]).view(3, 1, 1)
    for index, axis in enumerate(axes.flat):
        image, label = preview[index]
        image = (image * std_tensor + mean_tensor).clamp(0, 1).permute(1, 2, 0).numpy()
        axis.imshow(image.squeeze(), cmap="gray" if spec["grayscale"] else None)
        axis.set_title(class_names[int(label)]); axis.axis("off")
    figure.tight_layout(); figure.savefig(OUTPUT_DIR / f"{RUN_ID}_dataset_preview.png", dpi=150); plt.close(figure)

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
    else:
        gpu_name = "CPU"
    try:
        import torchvision
        torchvision_version = torchvision.__version__
    except Exception:
        torchvision_version = "unknown"
    try:
        import psutil
        cpu_count = psutil.cpu_count(logical=True)
        ram_total_mb = psutil.virtual_memory().total / (1024 * 1024)
    except ImportError:
        cpu_count = None
        ram_total_mb = None
    environment = {
        "python": __import__("sys").version.split()[0], "torch": torch.__version__,
        "torchvision": torchvision_version, "numpy": np.__version__,
        "platform": __import__("platform").platform(), "device": gpu_name,
        "accelerator": "Kaggle", "cpu_count": cpu_count, "ram_total_mb": ram_total_mb,
        "deterministic_algorithms": True, "torch_threads": torch.get_num_threads(),
        "git_commit": TRAINTRACE_GIT_COMMIT, "git_dirty": TRAINTRACE_GIT_DIRTY,
        "source_hashes": TRAINTRACE_SOURCE_HASHES,
    }
    results = {
        "run_id": RUN_ID, "best_val_acc": best_val_accuracy,
        "best_val_loss": history[best_epoch - 1]["val_loss"], "best_epoch": best_epoch,
        "total_training_time_sec": time.perf_counter() - total_start,
        "epochs_completed": len(history), "history": history,
        "gpu_device": gpu_name, "environment": environment,
        "dataset": dataset_snapshot, "split_sha256": split_sha256,
        "status": "COMPLETED",
    }
    (OUTPUT_DIR / "traintrace_results.json").write_text(json.dumps(results, indent=2, allow_nan=False))
    print("TrainTrace Kaggle run completed; metrics, charts, data split and checkpoints are in /kaggle/working.", flush=True)


if __name__ == "__main__":
    main()
