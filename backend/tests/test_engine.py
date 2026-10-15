import json
import sqlite3
import torch
import pytest
from PIL import Image
from torch.utils.data import TensorDataset, DataLoader
from core.models import get_model_by_name
from core.trainer import Trainer, train_one_epoch, evaluate, TrainingStopped
from core.dataset import get_cifar10_dataloaders, seed_worker
from domain import LaunchRun
from storage import sha256
from .conftest import tiny_loaders, decision_payload, complete
from db.database import database
from jobs import submit_run, submit_audit, stop_job
from worker import claim, work
from api.routers.runs import detail


@pytest.mark.parametrize(
    "architecture", ["custom_cnn", "resnet18", "mobilenet_v2", "efficientnet_b0"]
)
def test_architecture_compatibility(architecture):
    model = get_model_by_name(architecture).eval()
    with torch.inference_mode():
        assert model(torch.zeros(2, 3, 32, 32)).shape == (2, 10)
    with pytest.raises(ValueError):
        get_model_by_name("unknown")


def test_dataset_split_independent_of_initialization(monkeypatch, tmp_path):
    import torchvision

    class FakeCifar:
        def __init__(self, root, train, download, transform):
            self.transform = transform
            self.train = train

        def __len__(self):
            return 100 if self.train else 20

        def __getitem__(self, i):
            return self.transform(Image.new("RGB", (32, 32), (i, i, i))), i % 10

    monkeypatch.setattr(torchvision.datasets, "CIFAR10", FakeCifar)
    a = get_cifar10_dataloaders(
        batch_size=4, seed=0, split_seed=42, num_workers=0, data_dir=str(tmp_path)
    )
    b = get_cifar10_dataloaders(
        batch_size=4, seed=1, split_seed=42, num_workers=0, data_dir=str(tmp_path)
    )
    c = get_cifar10_dataloaders(
        batch_size=4, seed=0, split_seed=99, num_workers=0, data_dir=str(tmp_path)
    )
    assert a[0].dataset.indices == b[0].dataset.indices
    assert a[1].dataset.indices == b[1].dataset.indices
    assert a[0].dataset.indices != c[0].dataset.indices
    assert set(a[0].dataset.indices).isdisjoint(a[1].dataset.indices)
    assert next(iter(a[0]))[0].shape == (4, 3, 32, 32)
    seed_worker(0)


@pytest.mark.parametrize("scheduler", ["cosine", "step"])
def test_scheduler_checkpoint_contains_effective_config(scheduler, tmp_path):
    train, val, _ = tiny_loaders(batch_size=4, seed=0)
    t = Trainer(
        get_model_by_name("custom_cnn"),
        train,
        val,
        learning_rate=0.01,
        scheduler_type=scheduler,
        optimizer="sgd",
        device=torch.device("cpu"),
        save_dir=tmp_path,
        config={"seed": 0},
    )
    result = t.train(5, run_id="schedule")
    assert (
        len(result["learning_rates"]) == 5
        and result["learning_rates"][-1] < result["learning_rates"][0]
    )
    ckpt = torch.load(tmp_path / "schedule_epoch_5_checkpoint.pt", weights_only=True)
    assert ckpt["epoch"] == 5 and ckpt["config"]["seed"] == 0
    assert ckpt["scheduler_state_dict"]
    assert (tmp_path / "schedule_last_checkpoint.pt").is_file()


def test_training_nonfinite_empty_and_cancel(tmp_path):
    train, val, _ = tiny_loaders(batch_size=4)
    model = get_model_by_name("custom_cnn")
    criterion = torch.nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(model.parameters())
    empty = DataLoader(TensorDataset(torch.empty(0, 3, 32, 32), torch.empty(0, dtype=torch.long)))
    with pytest.raises(ValueError, match="Empty"):
        evaluate(model, empty, criterion, torch.device("cpu"))
    with pytest.raises(ValueError, match="Empty"):
        train_one_epoch(model, empty, criterion, opt, torch.device("cpu"))
    with pytest.raises(TrainingStopped):
        evaluate(model, val, criterion, torch.device("cpu"), lambda: True)
    nan_loader = DataLoader(
        TensorDataset(torch.full((2, 3, 32, 32), float("nan")), torch.zeros(2, dtype=torch.long)),
        batch_size=2,
    )
    with pytest.raises(ValueError, match="Non-finite"):
        train_one_epoch(model, nan_loader, criterion, opt, torch.device("cpu"))
    with pytest.raises(ValueError):
        Trainer(model, train, val, optimizer="invalid")
    t = Trainer(model, train, val, save_dir=tmp_path)
    with pytest.raises(ValueError):
        t.train(0)
    with pytest.raises(TrainingStopped):
        t.train(1, cancel=lambda: True)


def test_constraints_and_branches(client, config, completed):
    with pytest.raises(ValueError):
        LaunchRun(**{**config.model_dump(), "predecessor_run_id": completed["id"]})
    child = config.model_copy(
        update={
            "run_id": "child",
            "predecessor_run_id": completed["id"],
            "motivating_reason": "underfitting",
        }
    )
    with pytest.raises(ValueError, match="limitations"):
        submit_run(child)
    with pytest.raises(ValueError):
        submit_run(config.model_copy(update={"run_id": "other", "experiment_id": "missing"}))
    with database() as c:
        c.execute("UPDATE experiments SET archived=1 WHERE id='exp_test'")
    with pytest.raises(ValueError):
        submit_run(config.model_copy(update={"run_id": "other"}))
    with database() as c:
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO epoch_metrics(run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec) VALUES(?,1,1,1,1,1,1)",
                (config.run_id,),
            )


def test_second_selection_and_registry_version_collision(client, selected, config):
    assert (
        client.post(
            "/api/v1/registry/register",
            json={"name": "release", "version": "v1.0.0", "run_id": selected["id"]},
        ).status_code
        == 201
    )
    from .test_lifecycle import register

    model = client.get("/api/v1/registry/models").json()["models"][0]
    from registry.model_registry import ModelRegistry

    original = ModelRegistry().get_model(model["id"])
    digest = sha256(original["checkpoint_path"])
    other = complete(config.model_copy(update={"run_id": "other", "seed": 1}))
    assert (
        client.post("/api/v1/experiments/decisions", json=decision_payload(other["id"])).status_code
        == 409
    )
    client.post(
        "/api/v1/experiments/decisions",
        json={**decision_payload(selected["id"]), "status": "SUPERSEDED"},
    )
    assert (
        client.post("/api/v1/experiments/decisions", json=decision_payload(other["id"])).status_code
        == 201
    )
    assert register(client, other["id"]).status_code == 409
    assert ModelRegistry().get_model(model["id"])["run_id"] == selected["id"]
    assert sha256(original["checkpoint_path"]) == digest


def test_audit_mismatch_and_stopped_audit(client, completed):
    from domain import AuditRequest

    with database() as c:
        env = json.loads(
            c.execute(
                "SELECT environment_json FROM runs WHERE id=?", (completed["id"],)
            ).fetchone()[0]
        )
        env["python"] = "different"
        c.execute(
            "UPDATE runs SET environment_json=? WHERE id=?", (json.dumps(env), completed["id"])
        )
    submit_audit(AuditRequest(run_id=completed["id"]), "A")
    work(claim())
    audit = detail(completed["id"])["audits"][0]
    assert audit["report"]["passed"] is False and audit["report"]["environment_match"] is False
    job = submit_audit(AuditRequest(run_id=completed["id"]), "B")
    stop_job(job["job_id"])
    assert claim() is None
