"""
traintrace/backend/api/main.py
==============================
FastAPI Web Application Entrypoint for TrainTrace REST API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from api.routers import experiments, runs, registry, inference

# Initialize FastAPI App Instance
app = FastAPI(
    title="TrainTrace REST API",
    description="Evidence-based PyTorch Experiment Tracking, Decision Traceability & Inference Server",
    version="1.0.0"
)

# Configure CORS for React Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from React frontend (http://localhost:3000)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initializes SQLite Database schema on application startup."""
    init_db()


@app.get("/", tags=["Health Check"])
def root_endpoint():
    """Root health check endpoint."""
    return {
        "status": "online",
        "service": "TrainTrace REST API Server",
        "docs_url": "/docs"
    }


# Register REST Routers
app.include_router(experiments.router)
app.include_router(runs.router)
app.include_router(registry.router)
app.include_router(inference.router)
