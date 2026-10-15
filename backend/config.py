"""
traintrace/config.py
====================
Centralized Configuration Module for TrainTrace (Tracked Training Pipeline).

Senior Engineering Rationale:
-----------------------------
1. Centralizes all filesystem paths, database URIs, and default hyperparameters.
2. Automatically creates required storage directories on system initialization.
3. Uses pathlib.Path for cross-platform path handling (macOS, Linux, Windows).
4. Provides dynamic, platform-agnostic hardware device selection (NVIDIA CUDA, Hardware GPU Accelerator, or CPU).
"""

from pathlib import Path
import os
import torch

# -----------------------------------------------------------------------------
# 1. BASE SYSTEM DIRECTORIES
# -----------------------------------------------------------------------------
# Determine root directory of the TrainTrace repository dynamically.
# pathlib.Path(__file__).resolve().parent gives the absolute path to traintrace/
BASE_DIR = Path(__file__).resolve().parent

# Path to embedded documentation directory at repository root
DOCS_DIR = BASE_DIR.parent / "docs"

# Artifacts & Storage Sinks Directory Structure
STORAGE_DIR = Path(os.getenv("TRAINTRACE_STORAGE_DIR", str(BASE_DIR / "storage"))).resolve()
DATA_DIR = Path(
    os.getenv("TRAINTRACE_DATA_DIR", str(STORAGE_DIR / "data"))
).resolve()  # Raw & preprocessed dataset storage (CIFAR-10)
DATABASE_DIR = STORAGE_DIR / "db"  # SQLite database storage directory
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"  # Checkpoints (.pt), plots, JSON eval reports
REGISTRY_DIR = STORAGE_DIR / "registry"  # Promoted production model packages

# Automatically ensure all physical storage directories exist on disk when config is imported.
# mkdir(parents=True, exist_ok=True) creates missing parent directories safely.
for directory in [DATA_DIR, DATABASE_DIR, ARTIFACTS_DIR, REGISTRY_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 2. DATABASE CONFIGURATION
# -----------------------------------------------------------------------------
# Absolute path to the SQLite database file
DB_PATH = DATABASE_DIR / "traintrace.db"

# SQLAlchemy-compatible or SQLite connection string URI
DATABASE_URL = f"sqlite:///{DB_PATH}"

# -----------------------------------------------------------------------------
# 3. DEFAULT EXPERIMENT & PYTORCH HYPERPARAMETERS
# -----------------------------------------------------------------------------
# Benchmark workload constants
DEFAULT_BENCHMARK_DATASET = "CIFAR-10"  # Target classification workload
DEFAULT_BATCH_SIZE = 128  # Standard mini-batch size balancing speed & memory
DEFAULT_NUM_EPOCHS = 30  # Baseline training epoch count
DEFAULT_LEARNING_RATE = 0.001  # Default AdamW/SGD learning rate
DEFAULT_RANDOM_SEED = 42  # Random seed for reproducible weight initialization & data split
DEFAULT_NUM_WORKERS = 2  # Number of parallel DataLoader worker subprocesses


# -----------------------------------------------------------------------------
# 4. HARDWARE COMPUTATION DEVICE SELECTION
# -----------------------------------------------------------------------------
def get_default_device() -> torch.device:
    """
    Dynamically select the optimal compute execution target on the host system.
    Supports environment override via TRAINTRACE_DEVICE (e.g., 'cuda', 'mps', 'cpu').

    Priority Order:
    1. TRAINTRACE_DEVICE environment variable override (if valid)
    2. CUDA (NVIDIA GPU acceleration)
    3. MPS (Hardware GPU acceleration)
    4. CPU (Universal fallback execution)
    """
    env_override = os.getenv("TRAINTRACE_DEVICE", "").strip().lower()
    if env_override:
        if env_override == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        elif (
            env_override == "mps"
            and hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return torch.device("mps")
        elif env_override == "cpu":
            return torch.device("cpu")

    if torch.cuda.is_available():
        return torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")


def get_device_info() -> dict:
    """
    Returns platform-agnostic hardware metadata for the active compute device.
    """
    dev = get_default_device()
    dev_type = dev.type

    if dev_type == "cuda":
        name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NVIDIA CUDA"
        badge = "CUDA Accelerator Online"
        desc = f"NVIDIA CUDA ({name})"
    elif dev_type == "mps":
        badge = "GPU Accelerator Online"
        desc = "PyTorch Hardware Accelerator (GPU Engine)"
    else:
        badge = "CPU Compute Online"
        desc = "Host CPU (Universal Execution)"

    return {
        "type": dev_type,
        "name": desc,
        "badge": badge,
        "is_accelerated": dev_type in ["cuda", "mps"],
    }
