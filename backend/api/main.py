"""Local single-user API. Training runs in one separately scheduled worker."""

import os
import subprocess
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, database
from api.routers import experiments, runs, registry, inference, cloud
from config import BASE_DIR, get_device_info
from importlib import metadata
from process_lock import try_lock, unlock


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


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "TRAINTRACE_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="TrainTrace", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
    from config import STORAGE_DIR

    lock = (STORAGE_DIR / "worker.lock").open("a+b")
    try:
        acquired = try_lock(lock)
        worker_online = not acquired
        if acquired:
            unlock(lock)
    finally:
        lock.close()
    try:
        pytorch_version = metadata.version("torch")
    except metadata.PackageNotFoundError:
        pytorch_version = "unknown"
    return {
        "status": "online",
        "hardware": get_device_info(),
        "pytorch_version": pytorch_version,
        "active_job": dict(active) if active else None,
        "queued_jobs": queued,
        "worker_online": worker_online,
        "access_mode": "local single-user",
    }


for router in [experiments.router, runs.router, registry.router, inference.router, cloud.router]:
    app.include_router(router)
