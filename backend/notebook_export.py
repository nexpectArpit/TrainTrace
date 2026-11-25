"""Build a self-contained, per-run Colab/Jupyter training notebook."""

import json
from pathlib import Path

from core.dataset_contract import dataset_spec, preprocessing_contract


def _template(name):
    return Path(__file__).with_name("notebook_templates").joinpath(name).read_text(encoding="utf-8")


def _cell(kind, source):
    return {
        "cell_type": kind,
        "metadata": {},
        "source": source.splitlines(keepends=True),
        **({"outputs": [], "execution_count": None} if kind == "code" else {}),
    }


def build_notebook(run, model_source: str) -> bytes:
    config = run.get("config") or {}
    required = (
        "dataset_name",
        "model_name",
        "epochs",
        "batch_size",
        "learning_rate",
        "seed",
        "split_seed",
        "pretrained",
        "optimizer",
        "weight_decay",
        "scheduler_type",
        "architecture_config",
    )
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Saved run configuration is missing: {', '.join(missing)}")
    if config.get("initialize_from_run_id"):
        raise ValueError(
            "This run initialized from another checkpoint; a standalone notebook cannot reproduce it without those weights"
        )
    dataset, spec = dataset_spec(str(config["dataset_name"]))
    model = config["model_name"]
    preprocessing_contract(dataset, bool(config["pretrained"]), model)
    settings = {"classes": spec["num_classes"]}
    run_config = {
        "source_run_id": run["id"],
        "experiment_id": run.get("experiment_id"),
        "approach_name": run.get("approach_name", "Exported TrainTrace run"),
        "model_name": model,
        "dataset_name": dataset,
        "architecture_config": config["architecture_config"],
        "epochs": int(config["epochs"]),
        "batch_size": int(config["batch_size"]),
        "learning_rate": float(config["learning_rate"]),
        "seed": int(config["seed"]),
        "split_seed": int(config["split_seed"]),
        "pretrained": bool(config["pretrained"]),
        "optimizer": config["optimizer"],
        "weight_decay": float(config["weight_decay"]),
        "scheduler_type": config["scheduler_type"],
    }
    # These values are inserted into Python code cells, so use Python literals
    # (True/False/None), not JSON literals (true/false/null).
    config_literal = repr(run_config)
    settings_literal = repr(settings)
    setup = (
        _template("setup.py")
        + f"\nCONFIG = {config_literal}\nDATASET = {settings_literal}\n"
        + "OUTPUT_DIR = Path('traintrace_export_' + CONFIG['source_run_id'])\n"
        + "OUTPUT_DIR.mkdir(exist_ok=True)\n"
        + "print('Device:', DEVICE)\n"
        + "print('Saved configuration:', json.dumps(CONFIG, indent=2))\n"
    )
    cells = [
        _cell(
            "markdown",
            f"# Reproduce TrainTrace run `{run['id']}`\n\n"
            "This notebook is a portable reproduction: it contains the saved run settings and the model/training code, downloads the dataset, trains a fresh model, and writes readable metrics, plots, and checkpoints. It does **not** need TrainTrace, its database, or its local artifact folders. Results produced here stay in this notebook runtime until you download them.\n\n"
            "The run's final test set is kept separate from training/validation. Set `RUN_FINAL_TEST = True` only when you are ready to evaluate this reproduction on that holdout set.\n",
        ),
        _cell("code", "%pip -q install torch torchvision pandas matplotlib\n"),
        _cell("code", setup),
        _cell(
            "markdown",
            "## Model definitions\n\nThese are the TrainTrace model classes embedded in the export, so this notebook can run independently of the project checkout.\n",
        ),
        _cell("code", model_source),
        _cell("code", dataset_contract_source_text()),
        _cell(
            "markdown",
            "## Dataset and preprocessing\n\nUses the saved dataset and seeds, a 90/10 train/validation split, TrainTrace normalization, and dataset-appropriate training augmentation (no horizontal digit flips). Test data is loaded only if final evaluation is enabled.\n",
        ),
        _cell("code", _template("dataset.py")),
        _cell(
            "markdown",
            "## Train and save the best validation checkpoint\n\nEpoch metrics are printed and saved as CSV. The best checkpoint is selected by validation accuracy.\n",
        ),
        _cell("code", _template("train.py")),
        _cell("code", _template("plots.py")),
        _cell(
            "markdown",
            "## Optional final holdout evaluation\n\nRun only after choosing a candidate from validation results. This evaluates the exported model on the dataset's test partition.\n",
        ),
        _cell("code", _template("holdout.py")),
        _cell(
            "markdown",
            "## Files produced\n\n`metrics.csv`, `training_curves.png`, and `best_model.pt` are in the `OUTPUT_DIR` printed above. In Colab, download them from the Files panel or zip that folder. This export starts a new training execution; it does not modify or update the original TrainTrace run.\n",
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, ensure_ascii=False).encode("utf-8")


def model_source_text() -> str:
    return Path(__file__).with_name("core").joinpath("models.py").read_text(encoding="utf-8")


def dataset_contract_source_text() -> str:
    return (
        Path(__file__).with_name("core").joinpath("dataset_contract.py").read_text(encoding="utf-8")
    )
