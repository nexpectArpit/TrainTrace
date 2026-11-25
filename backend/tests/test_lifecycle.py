import io
import csv
import json
import pytest
import torch
from PIL import Image
from domain import LaunchRun
from pydantic import ValidationError
from db.database import database, init_db
from .conftest import complete, decision_payload
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
    assert completed["final_evaluation"] is None
    assert completed["validation"]["validation_accuracy"] == completed["best_val_accuracy"]
    assert completed["validation"]["parameter_count"] == 620810
    assert completed["config"]["seed"] == 0
    assert completed["environment"]["deterministic_algorithms"]
    assert completed["dataset"]["counts"]["validation"] == 2
    assert completed["environment"]["snapshot_schema_version"] == 1
    assert completed["dataset"]["snapshot_schema_version"] == 1
    kinds = {a["kind"] for a in completed["artifacts"]}
    assert {"best", "last", "validation", "metrics_csv", "split"} <= kinds
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
    filtered = client.get(
        "/api/v1/runs/compare/exp_test?dataset_name=cifar10&optimizer=adamw&architecture_depth=3&validation_accuracy_min=0"
    ).json()
    assert len(filtered["comparison_matrix"]) == 1
    assert not client.get("/api/v1/runs/compare/exp_test?dataset_name=cifar100").json()[
        "comparison_matrix"
    ]
    assert not client.get("/api/v1/runs/compare/exp_test?status=FAILED").json()["comparison_matrix"]
    csv_report = client.get("/api/v1/experiments/exp_test/report.csv")
    assert csv_report.status_code == 200
    assert "validation_accuracy_percent" in csv_report.text
    assert completed["id"] in csv_report.text


def test_cifar100_train_register_and_inference(client, experiment, monkeypatch):
    from torch.utils.data import DataLoader, TensorDataset
    import tracking.tracker as tracker

    x = torch.rand(12, 3, 32, 32)
    y = torch.tensor([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 98, 99])
    dataset = TensorDataset(x, y)
    dataset.classes = [f"class_{index}" for index in range(100)]
    loaders = (
        DataLoader(torch.utils.data.Subset(dataset, range(8)), batch_size=4),
        DataLoader(torch.utils.data.Subset(dataset, range(8, 10)), batch_size=2),
        DataLoader(torch.utils.data.Subset(dataset, range(10, 12)), batch_size=2),
    )
    monkeypatch.setattr(tracker, "get_dataloaders", lambda **kwargs: loaders)
    config = LaunchRun(
        run_id="run_cifar100",
        experiment_id=experiment,
        approach_name="CIFAR-100 smoke candidate",
        dataset_name="cifar100",
        epochs=1,
        batch_size=4,
        seed=3,
    )
    run = complete(config)
    assert run["dataset"]["num_classes"] == 100
    assert run["final_evaluation"] is None
    assert (
        client.post(
            "/api/v1/experiments/decisions", json=decision_payload(config.run_id)
        ).status_code
        == 201
    )
    from worker import claim, work

    evaluation_job = client.post("/api/v1/runs/final-evaluation", json={"run_id": config.run_id})
    assert evaluation_job.status_code == 202, evaluation_job.text
    work(claim())
    run = detail(config.run_id)
    assert len(run["final_evaluation"]["confusion_matrix"]) == 100
    assert sum(map(sum, run["final_evaluation"]["confusion_matrix"])) == 2
    registered = client.post(
        "/api/v1/registry/register",
        json={"name": "cifar100", "version": "v1.0.0", "run_id": config.run_id},
    )
    assert registered.status_code == 201, registered.text
    model_id = registered.json()["model"]["id"]
    assert client.post(f"/api/v1/registry/{model_id}/activate").status_code == 200
    prediction = client.post(
        f"/api/v1/inference/predict?model_id={model_id}",
        files={"file": ("sample.png", image_bytes(), "image/png")},
    )
    assert prediction.status_code == 200, prediction.text
    body = prediction.json()
    assert body["dataset_name"] == "CIFAR-100"
    assert len(body["all_probabilities"]) == 100


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
    assert run["latest_decision"]["evidence"]["validation"] == completed["validation"]
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
    assert "Candidate comparison" in report and "Epoch metrics" in report


def test_decision_requires_validation(client, config):
    submit_run(config)
    assert (
        client.post(
            "/api/v1/experiments/decisions", json=decision_payload(config.run_id)
        ).status_code
        == 409
    )


def test_global_tag_and_metadata_search(client, config, experiment):
    assert (
        client.patch(
            f"/api/v1/experiments/{experiment}",
            json={
                "name": "Baseline",
                "objective": "Test scientific lifecycle",
                "hypothesis": "An optimizer will learn useful representations",
                "conclusion": "",
                "archived": False,
                "target_accuracy": None,
                "target_latency_ms": None,
                "tags": {"cohort": "pilot"},
            },
        ).status_code
        == 200
    )
    tagged = config.model_copy(update={"tags": {"cohort": "pilot"}})
    complete(tagged)
    response = client.get("/api/v1/runs/search?tag_key=cohort&tag_value=pilot")
    assert response.status_code == 200, response.text
    result = response.json()
    assert [item["id"] for item in result["runs"]] == [tagged.run_id]
    assert [item["id"] for item in result["experiments"]] == [experiment]
    filtered = client.get("/api/v1/runs/search?dataset_name=cifar10&architecture=custom_cnn&seed=0")
    assert tagged.run_id in [item["id"] for item in filtered.json()["runs"]]


def test_final_evaluation_emits_pdf_and_confusion_matrix(client, final_evaluated):
    run = final_evaluated
    by_kind = {artifact["kind"]: artifact["id"] for artifact in run["artifacts"]}
    assert "evaluation_report_pdf" in by_kind
    assert "confusion_matrix_png" in by_kind
    pdf = client.get(f"/api/v1/runs/artifacts/{by_kind['evaluation_report_pdf']}")
    png = client.get(f"/api/v1/runs/artifacts/{by_kind['confusion_matrix_png']}")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-1.4")
    assert png.status_code == 200 and png.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert run["final_evaluation"]["snapshot_schema_version"] == 1
    assert (
        client.post("/api/v1/experiments/decisions", json=decision_payload("missing")).status_code
        == 404
    )


def register(client, run_id, name="release", version="v1.0.0"):
    return client.post(
        "/api/v1/registry/register", json={"name": name, "version": version, "run_id": run_id}
    )


def test_reports_withhold_historical_test_values(client, final_evaluated):
    run = final_evaluated
    with database() as conn:
        row = conn.execute("SELECT final_evaluation_json FROM runs WHERE id=?", (run["id"],)).fetchone()
        evaluation = json.loads(row["final_evaluation_json"])
        evaluation["legacy_preselection_test_exposure"] = True
        conn.execute("UPDATE runs SET final_evaluation_json=? WHERE id=?", (json.dumps(evaluation), run["id"]))
    csv_response = client.get(f"/api/v1/experiments/{run['experiment_id']}/report.csv")
    assert csv_response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert rows and all(row["holdout_accuracy_percent"] == "" for row in rows)
    assert all(row["test_metric_status"] == "HISTORICAL_PRESELECTION" for row in rows)
    markdown = client.get(f"/api/v1/experiments/{run['experiment_id']}/report")
    assert markdown.status_code == 200
    assert "Historical test exposure" in markdown.text
    assert "No eligible final holdout values are displayed" in markdown.text


def test_registry_prediction_and_frozen_lineage(client, final_evaluated):
    selected = final_evaluated
    result = register(client, selected["id"])
    assert result.status_code == 201, result.text
    model = result.json()["model"]
    mid = model["id"]
    from config import REGISTRY_DIR

    path = REGISTRY_DIR / model["checkpoint_path"]
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
    listed = client.get("/api/v1/registry/models").json()["models"]
    release = next(item for item in listed if item["id"] == mid)
    assert release["decision_status"] == "SELECTED"
    assert release["dataset_name"] == "cifar10"
    assert release["source_approach"] == "Baseline CNN"
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


def test_missing_checkpoint_and_legacy(client, final_evaluated):
    selected = final_evaluated
    from storage import find_run_artifact

    checkpoint = find_run_artifact(
        selected["id"], selected["id"] + "_best_checkpoint.pt", "checkpoints"
    )
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
    (ARTIFACTS_DIR / path).write_bytes(b"changed")
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


def test_compare_completed_run_checkpoints_side_by_side(client, experiment, monkeypatch):
    from torch.utils.data import DataLoader, TensorDataset
    import tracking.tracker as tracker
    from storage import find_run_artifact

    x = torch.rand(12, 3, 32, 32)
    y = torch.arange(12) % 10
    dataset = TensorDataset(x, y)
    loaders = (
        DataLoader(torch.utils.data.Subset(dataset, range(8)), batch_size=4),
        DataLoader(torch.utils.data.Subset(dataset, range(8, 10)), batch_size=2),
        None,
    )
    monkeypatch.setattr(tracker, "get_dataloaders", lambda **kwargs: loaders)

    run_a = complete(
        LaunchRun(
            run_id="run_mnist_resnet",
            experiment_id=experiment,
            approach_name="MNIST ResNet-18",
            dataset_name="mnist",
            model_name="resnet18",
            epochs=1,
            batch_size=4,
            seed=11,
        )
    )
    run_b = complete(
        LaunchRun(
            run_id="run_mnist_effnet",
            experiment_id=experiment,
            approach_name="MNIST EfficientNet-B0",
            dataset_name="mnist",
            model_name="efficientnet_b0",
            epochs=1,
            batch_size=4,
            seed=12,
        )
    )
    queued_cfg = LaunchRun(
        run_id="run_mnist_queued",
        experiment_id=experiment,
        approach_name="Queued run",
        dataset_name="mnist",
        epochs=1,
        batch_size=4,
        seed=13,
    )
    submit_run(queued_cfg)

    cand_res = client.get("/api/v1/inference/candidates")
    assert cand_res.status_code == 200, cand_res.text
    cand_ids = [item["run_id"] for item in cand_res.json()["candidates"]]
    assert set(cand_ids) == {run_a["id"], run_b["id"]}
    assert queued_cfg.run_id not in cand_ids

    # Without ground truth: predictions & confidences only, final-test selection unchanged.
    no_label = client.post(
        "/api/v1/inference/compare-runs",
        files={"file": ("digit.png", image_bytes(), "image/png")},
        data={"run_ids": [run_a["id"], run_b["id"]]},
    )
    assert no_label.status_code == 200, no_label.text
    body = no_label.json()
    assert body["models_compared"] == 2
    assert body["same_dataset"] is True
    assert body["expected_label"] is None
    assert body["correct_count"] is None
    assert [r["run_id"] for r in body["results"]] == [run_a["id"], run_b["id"]]
    assert all(r["dataset_name"] == "MNIST" and r["is_correct"] is None for r in body["results"])
    assert all(abs(sum(r["all_probabilities"].values()) - 1.0) < 1e-5 for r in body["results"])

    # With ground truth digit: reports per-checkpoint match and rank.
    with_label = client.post(
        "/api/v1/inference/compare-runs",
        files={"file": ("digit.png", image_bytes(), "image/png")},
        data={"run_ids": [run_a["id"], run_b["id"]], "expected_label": "7"},
    )
    assert with_label.status_code == 200, with_label.text
    matched = with_label.json()
    assert matched["expected_label"] == "7"
    assert matched["evaluable_count"] == 2
    assert matched["correct_count"] == sum(1 for r in matched["results"] if r["is_correct"])
    for item in matched["results"]:
        assert item["expected_label"] == "7"
        assert item["expected_label_valid"] is True
        assert item["is_correct"] is (item["predicted_class"] == "7")
        assert 1 <= item["expected_class_rank"] <= 10
        assert 0.0 <= item["expected_class_confidence"] <= 1.0

    # Validation & integrity guards.
    assert (
        client.post(
            "/api/v1/inference/compare-runs",
            files={"file": ("digit.png", image_bytes(), "image/png")},
            data={"run_ids": [run_a["id"]], "expected_label": "not_a_digit"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/inference/compare-runs",
            files={"file": ("digit.png", image_bytes(), "image/png")},
            data={"run_ids": [run_a["id"], run_a["id"]]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/inference/compare-runs",
            files={"file": ("digit.png", image_bytes(), "image/png")},
            data={"run_ids": ["missing_run"]},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/inference/compare-runs",
            files={"file": ("digit.png", image_bytes(), "image/png")},
            data={"run_ids": [queued_cfg.run_id]},
        ).status_code
        == 409
    )

    # Final-test selection & active serving rules remain untouched.
    assert detail(run_a["id"])["final_evaluation"] is None
    assert detail(run_b["id"])["final_evaluation"] is None
    assert (
        client.post(
            "/api/v1/inference/predict",
            files={"file": ("digit.png", image_bytes(), "image/png")},
        ).status_code
        == 409
    )

    # Tampered checkpoint must be rejected with 409.
    ckpt_path = find_run_artifact(run_a["id"], f"{run_a['id']}_best_checkpoint.pt", "checkpoints")
    ckpt_path.write_bytes(b"corrupt")
    assert (
        client.post(
            "/api/v1/inference/compare-runs",
            files={"file": ("digit.png", image_bytes(), "image/png")},
            data={"run_ids": [run_a["id"], run_b["id"]]},
        ).status_code
        == 409
    )
