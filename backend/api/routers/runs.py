"""
traintrace/backend/api/routers/runs.py
======================================
FastAPI Router for Launching Runs & Experiment Comparison.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from tracking.tracker import ExperimentTracker
from db.database import get_db_connection
from db import repository

router = APIRouter(prefix="/api/v1/runs", tags=["Runs & Comparison"])


# =============================================================================
# SCHEMAS
# =============================================================================
class LaunchRunSchema(BaseModel):
    run_id: str
    experiment_id: str
    experiment_name: str = "CIFAR-10 Optimization"
    objective: str = "Identify optimal architecture and hyperparameters"
    approach_name: str
    model_name: str = "custom_cnn"  # custom_cnn, resnet18, mobilenet_v2, efficientnet_b0
    epochs: int = 5
    batch_size: int = 128
    learning_rate: float = 0.001
    seed: int = 42


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.post("/launch", status_code=202)
def launch_run_endpoint(payload: LaunchRunSchema, background_tasks: BackgroundTasks):
    """
    Launches a customized training run with hyperparameter specifications.
    Executes training asynchronously in background, logging metrics per epoch to SQLite.
    """
    tracker = ExperimentTracker(
        exp_id=payload.experiment_id,
        exp_name=payload.experiment_name,
        objective=payload.objective
    )
    
    # Execute training run in background task to avoid blocking REST request
    background_tasks.add_task(
        tracker.run_experiment,
        run_id=payload.run_id,
        approach_name=payload.approach_name,
        model_name=payload.model_name,
        epochs=payload.epochs,
        batch_size=payload.batch_size,
        lr=payload.learning_rate,
        seed=payload.seed
    )
    
    return {
        "message": f"Run '{payload.run_id}' launched successfully in background.",
        "run_id": payload.run_id,
        "experiment_id": payload.experiment_id,
        "hyperparameters": {
            "model_name": payload.model_name,
            "epochs": payload.epochs,
            "batch_size": payload.batch_size,
            "learning_rate": payload.learning_rate,
            "seed": payload.seed
        }
    }


@router.get("/compare/{exp_id}")
def compare_experiment_runs(exp_id: str):
    """
    Fetches side-by-side metric comparison across all runs in an experiment workspace.
    """
    conn = get_db_connection()
    exp = repository.get_experiment(conn, exp_id)
    if not exp:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found.")
        
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE experiment_id = ?;", (exp_id,))
    runs = [dict(r) for r in cursor.fetchall()]
    
    comparison_data = []
    for r in runs:
        metrics = repository.get_run_metrics(conn, r["id"])
        decisions = repository.get_decisions(conn, r["id"])
        
        best_acc = max([m["val_acc"] for m in metrics]) if metrics else None
        final_loss = metrics[-1]["val_loss"] if metrics else None
        
        comparison_data.append({
            "run_id": r["id"],
            "approach_name": r["approach_name"],
            "model_architecture": r["model_architecture"],
            "hyperparameters": {
                "batch_size": r["batch_size"],
                "epochs": r["epochs"],
                "learning_rate": r["learning_rate"],
                "seed": r["seed"]
            },
            "status": r["status"],
            "best_val_accuracy": best_acc,
            "final_val_loss": final_loss,
            "latest_decision": decisions[0] if decisions else None
        })
        
    conn.close()
    return {
        "experiment_id": exp_id,
        "experiment_name": exp["name"],
        "objective": exp["objective"],
        "total_runs": len(comparison_data),
        "comparison_matrix": comparison_data
    }
