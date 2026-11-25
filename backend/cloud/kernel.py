"""Build and submit a Kaggle kernel from the recorded TrainTrace run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from cloud.credentials import get_authenticated_api
from config import BASE_DIR, STORAGE_DIR

def generate_kernel_code(config: dict[str, Any]) -> str:
    """Build the Kaggle script from the same model definitions used locally."""
    template = Path(__file__).with_name("kaggle_runner.py").read_text()
    model_source = (BASE_DIR / "core" / "models.py").read_text()
    dataset_contract_source = (BASE_DIR / "core" / "dataset_contract.py").read_text()
    config_json = json.dumps(config, allow_nan=False)
    source_hashes = {
        str(path.relative_to(BASE_DIR)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BASE_DIR.rglob("*.py"))
        if "storage" not in path.parts and "tests" not in path.parts
    }
    try:
        git_commit = subprocess.check_output(
            ["git", "-C", str(BASE_DIR.parent), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        git_dirty = bool(subprocess.check_output(
            ["git", "-C", str(BASE_DIR.parent), "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip())
    except (OSError, subprocess.CalledProcessError):
        git_commit, git_dirty = None, None
    return (
        template.replace("__TT_CONFIG_JSON__", json.dumps(config_json))
        .replace("__TT_MODEL_SOURCE__", repr(model_source))
        .replace("__TT_DATASET_CONTRACT_SOURCE__", repr(dataset_contract_source))
        .replace("__TT_SOURCE_HASHES__", repr(source_hashes))
        .replace("__TT_GIT_COMMIT__", repr(git_commit))
        .replace("__TT_GIT_DIRTY__", repr(git_dirty))
    )

def dispatch_kaggle_run(config: dict[str, Any]) -> dict[str, Any]:
    """Package and push a GPU training kernel to Kaggle."""
    api, username = get_authenticated_api()
    run_id = config["run_id"]
    sanitized_id = "".join(c if c.isalnum() else "-" for c in run_id.lower()).strip("-")
    kernel_slug = f"traintrace-{sanitized_id}"[:60].rstrip("-")

    # Prepare local staging directory for kernel files
    staging_dir = STORAGE_DIR / "cloud_staging" / run_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Write train.py script
    script_content = generate_kernel_code(config)
    (staging_dir / "train.py").write_text(script_content)

    # Write kernel-metadata.json
    metadata = {
        "id": f"{username}/{kernel_slug}",
        "title": f"TrainTrace {sanitized_id}"[:50],
        "code_file": "train.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
    }
    with (staging_dir / "kernel-metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2)

    # Push to Kaggle API
    api.kernels_push(str(staging_dir))

    return {
        "status": "DISPATCHED",
        "kernel_id": f"{username}/{kernel_slug}",
        "username": username,
        "run_id": run_id,
        "staging_dir": str(staging_dir),
    }


