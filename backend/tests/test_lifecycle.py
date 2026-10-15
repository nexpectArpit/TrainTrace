import io
from pathlib import Path
import pytest
from PIL import Image
from domain import LaunchRun
from pydantic import ValidationError
from db.database import database, init_db
from .conftest import decision_payload
from jobs import submit_run
from worker import claim, work, recover
from api.routers.runs import detail
from storage import contained, sha256


def image_bytes(size=(64, 64)):
    b = io.BytesIO()
    Image.new("RGB", size).save(b, format="PNG")
    return b.getvalue()


@pytest.mark.parametrize(
    "change",
    [
        {"epochs": 0},
        {"batch_size": -1},
        {"learning_rate": -1},
        {"seed": -1},
        {"run_id": "../escape"},
        {"model_name": "unknown"},
        {"scheduler_type": "unknown"},
        {"extra": "silently discarded"},
        {"pretrained": True},
    ],
)
def test_launch_validation(config, change):
    with pytest.raises(ValidationError):
        LaunchRun(**{**config.model_dump(), **change})


def test_investigation_management(client, experiment):
    assert client.get("/api/v1/experiments/").json()["experiments"][0]["id"] == experiment
    assert (
        client.post(
            "/api/v1/experiments/",
            json={"id": experiment, "name": "x", "objective": "y", "hypothesis": "z"},
        ).status_code
        == 409
    )
    payload = {
        "name": "Updated",
        "objective": "Objective",
        "hypothesis": "Hypothesis",
        "conclusion": "Recorded",
        "archived": True,
    }
    assert client.patch("/api/v1/experiments/" + experiment, json=payload).json()["archived"] == 1
    assert client.get("/api/v1/experiments/missing").status_code == 404
    assert client.patch("/api/v1/experiments/missing", json=payload).status_code == 404
    assert client.get("/api/v1/experiments/" + experiment + "/report").status_code == 200


def test_queue_duplicate_stop_recovery(client, config):
    assert client.post("/api/v1/runs/launch", json=config.model_dump()).status_code == 202
    assert client.post("/api/v1/runs/launch", json=config.model_dump()).status_code == 409
    assert detail(config.run_id)["status"] == "QUEUED"
    assert client.post("/api/v1/runs/jobs/" + config.run_id + "/stop").status_code == 200
    assert detail(config.run_id)["status"] == "STOPPED"
    assert claim() is None
    assert client.post("/api/v1/runs/jobs/" + config.run_id + "/stop").status_code == 409
    assert client.post("/api/v1/runs/jobs/missing/stop").status_code == 409
    cfg = config.model_copy(update={"run_id": "interrupted"})
    submit_run(cfg)
    claim()
    with database() as c:
        c.execute("UPDATE runs SET status='RUNNING' WHERE id='interrupted'")
    recover()
    assert detail("interrupted")["status"] == "FAILED"
    assert client.get("/api/v1/runs/jobs").json()["jobs"][0]["status"] == "FAILED"


def test_single_claim_and_configuration(client, config):
    submit_run(config)
    submit_run(config.model_copy(update={"run_id": "other", "seed": 9}))
    assert claim()["id"] == config.run_id
    # Worker owns serial dispatch; two different payloads cannot reuse one run.
    assert detail("other")["config"]["seed"] == 9
    assert client.get("/api/v1/runs/missing/live-status").status_code == 404
    assert client.get("/api/v1/runs/compare/missing").status_code == 404
    assert (
        client.get("/api/v1/experiments/wrong/runs/" + config.run_id + "/metrics").status_code
        == 404
    )


def test_completed_run_artifacts_metrics(client, completed):
    assert len(completed["metrics"]) == 2
    assert completed["evaluation"]["samples"] == 2
    assert completed["evaluation"]["parameter_count"] == 620810
    assert sum(map(sum, completed["evaluation"]["confusion_matrix"])) == 2
    assert completed["config"]["seed"] == 0
    assert completed["environment"]["deterministic_algorithms"]
    assert completed["dataset"]["counts"]["validation"] == 2
    kinds = {a["kind"] for a in completed["artifacts"]}
    assert {"best", "last", "evaluation", "metrics_csv", "split"} <= kinds
    for a in completed["artifacts"]:
        response = client.get("/api/v1/runs/artifacts/" + a["id"])
        assert response.status_code == 200
    assert client.get("/api/v1/runs/artifacts/missing").status_code == 404
    live = client.get("/api/v1/runs/" + completed["id"] + "/live-status").json()
    assert live["status"] == "COMPLETED" and len(live["all_metrics"]) == 2
    assert (
        client.get(
            f"/api/v1/runs/{completed['id']}/live-status?after={live['next_cursor']}"
        ).json()["events"]
        == []
    )
    result = client.get(
        "/api/v1/runs/compare/exp_test?search=Baseline&architecture=custom_cnn&seed=0&accuracy_min=0"
    ).json()
    assert len(result["comparison_matrix"]) == 1
    assert not client.get("/api/v1/runs/compare/exp_test?status=FAILED").json()["comparison_matrix"]


def test_decision_contract_and_history(client, config, completed):
    bad = decision_payload(config.run_id)
    bad["decision_rationale"] = bad.pop("rationale")
    assert client.post("/api/v1/experiments/decisions", json=bad).status_code == 422
    for change in [{"status": "INVALID"}, {"rationale": ""}, {"limitations": " "}]:
        assert (
            client.post(
                "/api/v1/experiments/decisions", json={**decision_payload(config.run_id), **change}
            ).status_code
            == 422
        )
    for status in ["REJECTED", "SUPERSEDED", "SELECTED"]:
        assert (
            client.post(
                "/api/v1/experiments/decisions",
                json={**decision_payload(config.run_id), "status": status},
            ).status_code
            == 201
        )
    run = detail(config.run_id)
    assert len(run["decisions"]) == 3 and run["latest_decision"]["status"] == "SELECTED"
    assert run["latest_decision"]["evidence"]["evaluation"] == completed["evaluation"]
    successor = config.model_copy(
        update={
            "run_id": "successor",
            "predecessor_run_id": run["id"],
            "motivating_reason": "Investigate underfitting",
        }
    )
    assert submit_run(successor)["status"] == "QUEUED"
    assert detail("successor")["predecessor_run_id"] == run["id"]
    report = client.get("/api/v1/experiments/exp_test/report").text
    assert "REJECTED" in report and "Investigate underfitting" in report


def test_decision_requires_evaluation(client, config):
    submit_run(config)
    assert (
        client.post(
            "/api/v1/experiments/decisions", json=decision_payload(config.run_id)
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/experiments/decisions", json=decision_payload("missing")).status_code
        == 404
    )


def register(client, run_id, name="release", version="v1.0.0"):
    return client.post(
        "/api/v1/registry/register", json={"name": name, "version": version, "run_id": run_id}
    )


def test_registry_prediction_and_frozen_lineage(client, selected):
    result = register(client, selected["id"])
    assert result.status_code == 201, result.text
    model = result.json()["model"]
    mid = model["id"]
    path = Path(model["checkpoint_path"])
    digest = sha256(path)
    assert register(client, selected["id"], version="1.0.0").status_code == 409
    assert sha256(path) == digest
    lineage = client.get("/api/v1/registry/" + mid + "/lineage").json()
    assert lineage["verified"] and lineage["configuration"]["seed"] == 0
    # Later human decisions do not mutate historical registration evidence.
    client.post(
        "/api/v1/experiments/decisions",
        json={**decision_payload(selected["id"]), "status": "SUPERSEDED"},
    )
    assert (
        client.get("/api/v1/registry/" + mid + "/lineage").json()["decision"]["status"]
        == "SELECTED"
    )
    assert (
        client.post(
            "/api/v1/inference/predict", files={"file": ("x.png", image_bytes(), "image/png")}
        ).status_code
        == 409
    )
    assert client.post("/api/v1/registry/" + mid + "/activate").status_code == 200
    response = client.post(
        "/api/v1/inference/predict?model_id=" + mid,
        files={"file": ("x.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 200, response.text
    prediction = response.json()
    assert prediction["run_id"] == selected["id"] and prediction["model_id"] == mid
    assert abs(sum(prediction["all_probabilities"].values()) - 1) < 1e-5
    assert len(prediction["top_k"]) == 3
    assert (
        client.post(
            "/api/v1/inference/predict?model_id=wrong",
            files={"file": ("x.png", image_bytes(), "image/png")},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/inference/predict", files={"file": ("x.png", b"bad", "image/png")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/inference/predict", files={"file": ("x.txt", b"text", "text/plain")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/inference/predict",
            files={"file": ("x.png", b"a" * (5 * 1024 * 1024 + 1), "image/png")},
        ).status_code
        == 413
    )
    path.write_bytes(b"corrupt")
    assert client.post("/api/v1/registry/" + mid + "/activate").status_code == 409
    assert (
        client.post(
            "/api/v1/inference/predict", files={"file": ("x.png", image_bytes(), "image/png")}
        ).status_code
        == 409
    )


def test_registry_invalid_candidates(client, config, completed):
    assert register(client, config.run_id).status_code == 409
    assert register(client, "missing").status_code == 409
    assert register(client, config.run_id, name="../escape").status_code == 422
    assert register(client, config.run_id, version="v1").status_code == 422
    assert client.get("/api/v1/registry/missing/lineage").status_code == 404


def test_missing_checkpoint_and_legacy(client, selected):
    from config import ARTIFACTS_DIR

    checkpoint = ARTIFACTS_DIR / (selected["id"] + "_best_checkpoint.pt")
    checkpoint.unlink()
    assert register(client, selected["id"]).status_code == 409
    with database() as c:
        c.execute(
            "INSERT INTO models(id,name,version,run_id,checkpoint_path,status) VALUES('legacy','legacy','v1',?,'unknown','PROMOTED')",
            (selected["id"],),
        )
    assert client.get("/api/v1/registry/legacy/lineage").json()["verified"] is False
    assert client.post("/api/v1/registry/legacy/activate").status_code == 409


def test_audits_replay_original_and_persist(client, completed):
    for protocol in ["A", "B"]:
        response = client.post(
            "/api/v1/runs/audit/protocol-" + protocol.lower(), json={"run_id": completed["id"]}
        )
        assert response.status_code == 202
        work(claim())
        run = detail(completed["id"])
        report = next(a["report"] for a in run["audits"] if a["protocol"] == protocol)
        assert report, run["audits"]
        assert report["configuration"]["epochs"] == 2 and report["configuration"]["seed"] == 0
        if protocol == "A":
            assert report["passed"], report
        else:
            assert report["sample_count"] == 5 and report["fixed_split"]
            assert report["min_accuracy"] <= report["mean_accuracy"] <= report["max_accuracy"]
    assert (
        client.post(
            "/api/v1/runs/audit/protocol-b", json={"run_id": completed["id"], "seeds": [1, 1]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/runs/audit/protocol-b", json={"run_id": completed["id"], "seeds": []}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/v1/runs/audit/protocol-a", json={"run_id": "missing"}).status_code == 409
    )


def test_failure_preserves_completed_epoch(client, config, monkeypatch):
    from core.trainer import Trainer

    original = Trainer.train

    def failing(self, *args, **kwargs):
        original_epoch = args[4]

        def persist_then_fail(epoch, metrics):
            original_epoch(epoch, metrics)
            if epoch == 2:
                raise RuntimeError("Injected failure after persistent metrics")

        args = list(args)
        args[4] = persist_then_fail
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Trainer, "train", failing)
    submit_run(config)
    work(claim())
    run = detail(config.run_id)
    assert run["status"] == "FAILED" and len(run["metrics"]) == 2
    assert any(a["kind"] == "last" for a in run["artifacts"])
    assert "Injected failure" in run["error"]


def test_stop_active_run(client, config, monkeypatch):
    import tracking.tracker as tracker

    count = 0

    def cancel(job_id):
        nonlocal count
        count += 1
        return count > 4

    monkeypatch.setattr(tracker, "cancelled", cancel)
    submit_run(config)
    work(claim())
    assert detail(config.run_id)["status"] == "STOPPED"


def test_artifact_containment_and_tamper(client, completed):
    from config import ARTIFACTS_DIR

    with pytest.raises(ValueError):
        contained(ARTIFACTS_DIR, "../escape")
    artifact = completed["artifacts"][0]
    with database() as c:
        path = c.execute("SELECT path FROM artifacts WHERE id=?", (artifact["id"],)).fetchone()[0]
    Path(path).write_bytes(b"changed")
    assert client.get("/api/v1/runs/artifacts/" + artifact["id"]).status_code == 409


def test_migration_preserves_legacy_rows(client, config):
    submit_run(config)
    with database() as c:
        c.execute("PRAGMA user_version=0")
    init_db()
    init_db()
    assert detail(config.run_id)["id"] == config.run_id
    assert client.get("/").json()["status"] == "online"
    assert client.get("/api/v1/system/info").status_code == 200
