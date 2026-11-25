"""FastAPI router for Cloud GPU execution and status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from cloud.credentials import (
    get_authenticated_api,
    get_kaggle_credentials,
    configure_kaggle_credentials,
    resolve_kaggle_username,
)
from cloud.kaggle_bridge import get_kaggle_run_status

router = APIRouter(prefix="/api/v1/cloud", tags=["Cloud Execution"])


class CloudConfigRequest(BaseModel):
    token: str | None = Field(None, description="Kaggle API token (KGAT_...)")
    username: str | None = Field(None, description="Kaggle username")
    key: str | None = Field(None, description="Kaggle API key")


@router.get("/status")
def cloud_status():
    """Return Kaggle API configuration and connection availability."""
    creds = get_kaggle_credentials()
    username = creds.get("username")
    authenticated = False
    connection_error = None
    if creds["configured"]:
        try:
            username = resolve_kaggle_username(force=False)
            authenticated = True
        except Exception as exc:
            connection_error = f"{type(exc).__name__}: {exc}"
    return {
        "provider": "kaggle",
        "configured": creds["configured"],
        "authenticated": authenticated,
        "connection_error": connection_error,
        "username": username,
        "source": creds.get("source"),
        "weekly_gpu_hours": 30,
        "gpu_accelerator": "NVIDIA Tesla T4 (16GB VRAM)",
        "help": creds.get("help"),
    }


@router.post("/configure")
def configure_cloud_credentials(payload: CloudConfigRequest):
    """Configure and verify Kaggle API credentials dynamically (BYOK - Bring Your Own Key)."""
    try:
        result = configure_kaggle_credentials(
            token=payload.token,
            username=payload.username,
            key=payload.key,
        )
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/verify")
def verify_cloud_connection():
    """Verify Kaggle authentication against the remote API."""
    try:
        api, username = get_authenticated_api(force=True)
        return {
            "authenticated": True,
            "username": username,
            "message": f"Successfully authenticated as Kaggle user: @{username}",
        }
    except Exception as exc:
        raise HTTPException(400, f"Kaggle authentication failed: {exc}") from exc


@router.get("/kernel-status/{kernel_id:path}")
def check_kernel(kernel_id: str):
    """Check status of a running remote Kaggle kernel."""
    return get_kaggle_run_status(kernel_id)

