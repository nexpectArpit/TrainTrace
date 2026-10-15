"""Local single-user API. Training runs in one separately scheduled worker."""

import os
import subprocess
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, database
from api.routers import experiments, runs, registry, inference
from config import BASE_DIR, get_device_info
import torch


@asynccontextmanager
async def lifespan(app):
    init_db()
    worker = None
    if os.getenv("TRAINTRACE_WORKER", "1") != "0":
        worker = subprocess.Popen([sys.executable, str(BASE_DIR / "worker.py")], cwd=BASE_DIR)
    yield
    if worker and worker.poll() is None:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()


app = FastAPI(title="TrainTrace", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def root_endpoint():
    return {"status": "online", "service": "TrainTrace", "docs_url": "/docs"}


@app.get("/api/v1/system/info")
def system_info_endpoint():
    with database() as c:
        active = c.execute("SELECT id,kind FROM jobs WHERE status='RUNNING'").fetchone()
        queued = c.execute("SELECT count(*) FROM jobs WHERE status='QUEUED'").fetchone()[0]
    import fcntl
    from config import STORAGE_DIR

    worker_online = False
    with (STORAGE_DIR / "worker.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
        except BlockingIOError:
            worker_online = True
    return {
        "status": "online",
        "hardware": get_device_info(),
        "pytorch_version": torch.__version__,
        "active_job": dict(active) if active else None,
        "queued_jobs": queued,
        "worker_online": worker_online,
        "access_mode": "local single-user",
    }


for router in [experiments.router, runs.router, registry.router, inference.router]:
    app.include_router(router)
