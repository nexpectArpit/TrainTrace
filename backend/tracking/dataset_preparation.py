"""Prepare datasets and publish measured download/extraction progress."""

import json
import os
import threading
import time
from urllib.request import Request, urlopen

import torchvision

from config import DATA_DIR


def load_training_data(config, dataset_key, spec, *, set_run, event, loader):
    """Return train/validation loaders and the preparation start timestamp."""
    run_id = config["run_id"]
    dataset_started = time.time()
    dataset_class = getattr(torchvision.datasets, spec["torchvision_name"])
    archive_name = getattr(dataset_class, "filename", None)
    archive_path = DATA_DIR / archive_name if archive_name else None
    initial_size = archive_path.stat().st_size if archive_path and archive_path.is_file() else 0
    event(
        run_id,
        f"Preparing {spec['name']} dataset; download, verification, and extraction happen before epoch 1.",
    )
    set_run(
        run_id,
        progress_json=json.dumps(
            {
                "phase": "dataset_preparation",
                "dataset": spec["name"],
                "started_at": dataset_started,
                "downloaded_bytes": initial_size,
            }
        ),
    )
    loader_options = {
        "batch_size": config["batch_size"],
        "seed": config["seed"],
        "split_seed": config["split_seed"],
        # Use 2 DataLoader workers on macOS/Linux to overlap image decoding
        # with model compute. Keep 0 in edge cases (Windows or env override)
        # because PyTorch multiprocessing spawn has higher IPC cost there.
        # For pretrained runs (224×224 PIL resize), 2 workers give the most
        # benefit by parallelising the CPU-bound resize pipeline.
        "num_workers": int(os.getenv("TRAINTRACE_NUM_WORKERS", "2")),
        "pretrained": config["pretrained"],
        "include_test": False,
    }
    stop_dataset_monitor = threading.Event()

    def monitor_dataset_preparation():
        total_bytes = None
        source_url = getattr(dataset_class, "url", None)
        if archive_path and isinstance(source_url, str):
            try:
                with urlopen(Request(source_url, method="HEAD"), timeout=6) as response:
                    total_bytes = int(response.headers.get("Content-Length") or 0) or None
            except (OSError, ValueError):
                pass
        while not stop_dataset_monitor.wait(1):
            downloaded = (
                archive_path.stat().st_size if archive_path and archive_path.is_file() else 0
            )
            set_run(
                run_id,
                progress_json=json.dumps(
                    {
                        "phase": "dataset_preparation",
                        "dataset": spec["name"],
                        "started_at": dataset_started,
                        "elapsed_seconds": round(time.time() - dataset_started, 1),
                        "downloaded_bytes": downloaded,
                        "download_total_bytes": total_bytes,
                    }
                ),
            )

    monitor = threading.Thread(target=monitor_dataset_preparation, daemon=True)
    monitor.start()
    try:
        loaders = loader(dataset_name=dataset_key, **loader_options)
    finally:
        stop_dataset_monitor.set()
        monitor.join(timeout=2)
    train, val, _ = loaders
    return train, val, dataset_started
