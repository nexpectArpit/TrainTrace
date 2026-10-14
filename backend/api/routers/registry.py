"""
traintrace/backend/api/routers/registry.py
===========================================
FastAPI Router for Model Registry Promotion and Lineage Graph Queries.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from registry.model_registry import ModelRegistry

router = APIRouter(prefix="/api/v1/registry", tags=["Model Governance & Lineage"])
registry = ModelRegistry()


class ModelPromoteSchema(BaseModel):
    name: str
    run_id: str
    version: str = "v1.0"
    test_accuracy: Optional[float] = None
    latency_ms: Optional[float] = None


@router.post("/promote", status_code=201)
def promote_model_endpoint(payload: ModelPromoteSchema):
    """
    Promotes an evaluated run candidate into a versioned production model catalog package.
    """
    try:
        res = registry.promote_candidate(
            name=payload.name,
            run_id=payload.run_id,
            version=payload.version,
            test_accuracy=payload.test_accuracy,
            latency_ms=payload.latency_ms
        )
        return {"message": "Model promoted successfully", "details": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/lineage")
def get_model_lineage_endpoint(model_id: str):
    """
    Fetches 11-step complete Lineage & Provenance Graph for a registered model version.
    """
    try:
        return registry.get_lineage(model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
