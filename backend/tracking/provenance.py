"""Capture the exact training environment and checkpoint tensor identity."""

import hashlib
import platform
import subprocess
import sys

import numpy as np
import torch
import torchvision

from config import BASE_DIR, get_device_info
from storage import sha256


def checkpoint_state_sha256(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    digest = hashlib.sha256()
    for name, tensor in sorted(checkpoint["model_state_dict"].items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(value.dtype).encode())
        digest.update(str(tuple(value.shape)).encode())
        # Reshape first so scalar buffers (for example BatchNorm's
        # num_batches_tracked) can be reinterpreted as raw bytes too.
        digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


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
