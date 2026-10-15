from fastapi import APIRouter, HTTPException
from domain import RegisterModel
from registry.model_registry import ModelRegistry
from db.database import database

router = APIRouter(prefix="/api/v1/registry", tags=["Registry"])
registry = ModelRegistry()
ModelPromoteSchema = RegisterModel


@router.get("/models")
def list_models_endpoint():
    with database() as c:
        rows = [
            dict(r)
            for r in c.execute(
                "SELECT id,name,version,run_id,test_accuracy,latency_ms,status,sha256,created_at FROM models ORDER BY created_at DESC,id"
            )
        ]
        active = c.execute("SELECT model_id FROM serving WHERE id=1").fetchone()
    return {"models": rows, "active_model_id": active[0] if active else None}


@router.post("/register", status_code=201)
@router.post("/promote", status_code=201, deprecated=True)
def promote_model_endpoint(payload: RegisterModel):
    try:
        return {
            "model": registry.promote_candidate(**payload.model_dump()),
            "message": "Version registered. Activate it separately for inference.",
        }
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{model_id}/activate")
def activate(model_id: str):
    try:
        return registry.activate(model_id)
    except (ValueError, KeyError, RuntimeError) as e:
        raise HTTPException(409, str(e)) from e


@router.get("/{model_id}/lineage")
def get_model_lineage_endpoint(model_id: str):
    try:
        return registry.get_lineage(model_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
