"""
traintrace/backend/api/routers/experiments.py
=============================================
FastAPI Router for Experiment, Run, Metric, and Decision Rationale REST Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db_connection
from db import repository

router = APIRouter(prefix="/api/v1/experiments", tags=["Experiments & Runs"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================
class ExperimentCreateSchema(BaseModel):
    id: str
    name: str
    objective: str
    target_accuracy: Optional[float] = None
    target_latency_ms: Optional[float] = None


class DecisionRecordSchema(BaseModel):
    run_id: str
    status: str  # ACCEPTED, REJECTED, SUPERSEDED, SELECTED
    rationale: str


# =============================================================================
# REST ENDPOINTS
# =============================================================================
@router.post("/", status_code=201)
def create_experiment_endpoint(payload: ExperimentCreateSchema):
    """Creates a new experiment parent workspace."""
    conn = get_db_connection()
    existing = repository.get_experiment(conn, payload.id)
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Experiment '{payload.id}' already exists.")
        
    repository.create_experiment(
        conn, payload.id, payload.name, payload.objective, payload.target_accuracy, payload.target_latency_ms
    )
    conn.close()
    return {"message": "Experiment created successfully", "experiment_id": payload.id}


@router.get("/{exp_id}")
def get_experiment_endpoint(exp_id: str):
    """Fetches details for a single experiment."""
    conn = get_db_connection()
    exp = repository.get_experiment(conn, exp_id)
    conn.close()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return exp


@router.get("/{exp_id}/runs/{run_id}/metrics")
def get_run_metrics_endpoint(exp_id: str, run_id: str):
    """Fetches per-epoch metric curves for a specific run."""
    conn = get_db_connection()
    metrics = repository.get_run_metrics(conn, run_id)
    conn.close()
    return {"run_id": run_id, "epoch_metrics": metrics}


@router.post("/decisions", status_code=201)
def record_decision_endpoint(payload: DecisionRecordSchema):
    """Records human decision status and rationale for an approach run."""
    conn = get_db_connection()
    run = repository.get_run(conn, payload.run_id)
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Run '{payload.run_id}' not found.")
        
    repository.save_decision(conn, payload.run_id, payload.status, payload.rationale)
    decisions = repository.get_decisions(conn, payload.run_id)
    conn.close()
    return {"message": "Decision rationale recorded successfully", "decisions": decisions}
