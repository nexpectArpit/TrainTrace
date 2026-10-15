import os
import sys
import tempfile
from pathlib import Path

os.environ["TRAINTRACE_STORAGE_DIR"] = tempfile.mkdtemp(prefix="traintrace-tests-")
os.environ["TRAINTRACE_WORKER"] = "0"
os.environ["TRAINTRACE_DEVICE"] = "cpu"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import torch
from fastapi.testclient import TestClient
from api.main import app
from db.database import init_db
from domain import LaunchRun
import tracking.tracker as tracker


def tiny_loaders(**kwargs):
    # Independent deterministic split; initialization seed controls loader order only.
    from torch.utils.data import DataLoader, TensorDataset, Subset

    generator = torch.Generator().manual_seed(314)
    x = torch.rand(12, 3, 32, 32, generator=generator)
    y = torch.arange(12) % 10
    ds = TensorDataset(x, y)
    return tuple(
        DataLoader(
            Subset(ds, indices),
            batch_size=kwargs.get("batch_size", 4),
            shuffle=i == 0,
            generator=torch.Generator().manual_seed(kwargs.get("seed", 42)),
        )
        for i, indices in enumerate([list(range(8)), [8, 9], [10, 11]])
    )


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    torch.set_num_threads(1)
    init_db()
    from db.database import get_db_connection

    c = get_db_connection()
    c.execute("PRAGMA foreign_keys=OFF")
    for t in [
        "serving",
        "models",
        "decisions",
        "events",
        "artifacts",
        "audits",
        "jobs",
        "epoch_metrics",
        "runs",
        "experiments",
    ]:
        c.execute(f"DELETE FROM {t}")
    c.commit()
    c.close()
    from config import ARTIFACTS_DIR, REGISTRY_DIR

    for root in [ARTIFACTS_DIR, REGISTRY_DIR]:
        for path in root.iterdir():
            if path.is_file():
                path.unlink()
    monkeypatch.setattr(tracker, "get_cifar10_dataloaders", tiny_loaders)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def experiment(client):
    payload = {
        "id": "exp_test",
        "name": "Baseline",
        "objective": "Test scientific lifecycle",
        "hypothesis": "An optimizer will learn useful representations",
    }
    assert client.post("/api/v1/experiments/", json=payload).status_code == 201
    return payload["id"]


@pytest.fixture
def config(experiment):
    return LaunchRun(
        run_id="run_test",
        experiment_id=experiment,
        approach_name="Baseline CNN",
        epochs=2,
        batch_size=4,
        seed=0,
    )


def complete(config):
    from jobs import submit_run
    from worker import claim, work

    submit_run(config)
    work(claim())
    from api.routers.runs import detail

    run = detail(config.run_id)
    assert run["status"] == "COMPLETED", run["error"]
    return run


def decision_payload(run_id):
    return {
        "run_id": run_id,
        "status": "SELECTED",
        "rationale": "Measured holdout and validation evidence supports this candidate",
        "limitations": "Small synthetic test; no production quality claim",
        "alternatives_considered": "Another optimizer",
        "why_not_alternative": "No measured advantage yet",
        "tradeoff_acknowledged": "Larger model requires more compute",
        "next_investigation": "Evaluate more data",
    }


@pytest.fixture
def completed(config):
    return complete(config)


@pytest.fixture
def selected(client, completed):
    response = client.post("/api/v1/experiments/decisions", json=decision_payload(completed["id"]))
    assert response.status_code == 201, response.text
    return completed
