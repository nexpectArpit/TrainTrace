"""
traintrace/config.py
====================
Centralized Configuration Module for TrainTrace (Tracked Training Pipeline).

Senior Engineering Rationale:
-----------------------------
1. Centralizes all filesystem paths, database URIs, and default hyperparameters.
2. Automatically creates required storage directories on system initialization.
3. Uses pathlib.Path for cross-platform path handling (macOS, Linux, Windows).
4. Provides dynamic hardware device selection (NVIDIA CUDA, Apple Silicon MPS, or CPU).
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
STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = STORAGE_DIR / "data"              # Raw & preprocessed dataset storage (CIFAR-10)
DATABASE_DIR = STORAGE_DIR / "db"            # SQLite database storage directory
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"    # Checkpoints (.pt), plots, JSON eval reports
REGISTRY_DIR = STORAGE_DIR / "registry"      # Promoted production model packages

# Automatically ensure all physical storage directories exist on disk when config is imported.
# mkdir(parents=True, exist_ok=True) creates missing parent directories safely.
for directory in [DATA_DIR, DATABASE_DIR, ARTIFACTS_DIR, REGISTRY_DIR, DOCS_DIR]:
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
DEFAULT_BATCH_SIZE = 128                # Standard mini-batch size balancing speed & memory
DEFAULT_NUM_EPOCHS = 30                 # Baseline training epoch count
DEFAULT_LEARNING_RATE = 0.001           # Default AdamW/SGD learning rate
DEFAULT_RANDOM_SEED = 42                # Random seed for reproducible weight initialization & data split
DEFAULT_NUM_WORKERS = 2                 # Number of parallel DataLoader worker subprocesses

# -----------------------------------------------------------------------------
# 4. HARDWARE COMPUTATION DEVICE SELECTION
# -----------------------------------------------------------------------------
def get_default_device() -> torch.device:
    """
    Dynamically select the optimal compute execution target on the host system.
    
    Priority Order:
    1. CUDA (NVIDIA GPU acceleration)
    2. MPS (Apple Silicon Metal Performance Shaders GPU acceleration)
    3. CPU (Universal fallback execution)
    
    Returns:
        torch.device: Configured PyTorch compute execution target.
    """
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")
