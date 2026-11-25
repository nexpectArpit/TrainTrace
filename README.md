# TrainTrace — Tracked Training Pipeline

TrainTrace is a local ML investigation workspace. It connects seeded PyTorch training, holdout evaluation, reproducibility studies, candidate comparisons, human decision history, immutable model versions, and version-bound inference.

The workspace supports **CIFAR-10, CIFAR-100, MNIST, Fashion-MNIST, and SVHN** on a single-user macOS/Linux workstation, with one local compute job at a time. Kaggle GPU execution is optional and requires your own credentials. The original product specification is in [docs/PRD](docs/PRD/Tracked_Training_Pipeline_PRD.md); the current refactor status is in [the MVP refactor plan](docs/architecture/MVP_REFACTOR_PLAN.md).

## Run locally

Use Python **3.13** and Node **22.12+** (Node 22 recommended). From this repository root:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open [the workspace](http://127.0.0.1:3000) and [API documentation](http://127.0.0.1:8000/docs). The API starts one worker subprocess automatically. Restart the API after backend source changes; worker code is not hot-reloaded. Keep a single API service for this local deployment. Bind to loopback: this application has no multi-user authentication and is not intended for public hosting.

### Inspect a run from the terminal

From the repository root, use the read-only inspector to find the latest main run and its metrics:

```sh
python3 scripts/inspect_run.py
python3 scripts/inspect_run.py --run-id YOUR_RUN_ID --all-epochs
python3 scripts/inspect_run.py --run-id YOUR_RUN_ID --json
```

The command prints the run status, latest saved epoch, latest sampled batch, errors, evaluation, and absolute artifact paths. By default it skips audit replay runs so a replay does not hide the latest run you launched. `--include-replays` selects the latest run of either kind. It honors `TRAINTRACE_STORAGE_DIR` and does not require the API or PyTorch to be running.

For code tracing: `backend/tracking/tracker.py` coordinates local training; `backend/tracking/progress_recorder.py` writes batch samples and epoch metrics; `backend/tracking/metrics_export.py` mirrors completed epochs into CSV. `backend/db/database.py` and `backend/db/migrations.py` define the tables. `backend/repositories/run_repository.py` reads saved metrics; `backend/api/routers/runs.py` serves run status; `frontend/src/app/useLiveRun.js` polls it; `frontend/src/features/training/RunExecutionPanel.jsx` displays the evidence. SQLite is the durable source; `backend/storage/artifacts/runs/<run-id>/metrics/<run-id>_metrics.csv` is its readable per-epoch copy.

### Artifact folders

Each run's files live under `backend/storage/artifacts/runs/<run-id>/`:

```text
checkpoints/  best, last, and periodic PyTorch checkpoints
metrics/      human-readable epoch CSV
reports/      validation, evaluation, audit JSON, and PDF reports
images/       generated dataset previews and confusion matrices
data/         split indices and related dataset evidence
```

The SQLite `artifacts.path` column stores a path relative to `backend/storage/artifacts`; use it when resolving a recorded artifact. A one-time organizer moves old flat files into this layout and updates those database paths. It backs up the database first and stops if a job is queued or running:

```sh
python3 scripts/organize_artifacts.py          # preview only
python3 scripts/organize_artifacts.py --apply  # organize existing files
```

Files with no artifact record are kept under `backend/storage/artifacts/legacy-untracked/`; the storage orphan cleanup excludes this archive. The organizer already ran for the local storage on 2026-11-18; rerunning it should report zero flat files. Set `TRAINTRACE_STORAGE_DIR` to organize another storage location.

Datasets download on first use, then work from their caches. ImageNet initialization also requires a first-use download. Existing cached datasets can be reused with `TRAINTRACE_DATA_DIR`. Local runs require no cloud account.

## Workflow

1. **Investigations:** define an objective, hypothesis, and optional accuracy/latency targets. Targets and all accuracy measurements use **0–100 percent**. Edit conclusions and archive investigations here.
2. **Training:** choose one of the five image datasets, configure an architecture, optimizer, schedule, initialization seed, and independent split seed. CustomCNN also exposes depth, width, classifier size, and dropout. Choose local execution or connect a Kaggle account for cloud execution. Queue a unique run ID. Completed epoch metrics persist immediately, and best/last/periodic checkpoints are catalogued with SHA256 checksums. A stopped or failed run retains completed evidence.
3. **Compare:** select up to four candidate runs and inspect validation trajectories, hyperparameters, measured parameter counts, holdout accuracy, checkpoint size, duration, and latency. The overfitting gap uses training and validation accuracy from the same final epoch.
4. **Audits:** Protocol A replays the original full configuration twice and compares exact numerical trajectories plus test loss/accuracy against the original. Timing is excluded. Conditions must match. Protocol B defaults to five distinct initialization seeds, holds the data split fixed, and persists per-seed test accuracies, mean, population standard deviation, minimum, maximum, and spread. Both use the same sequential queue as ordinary training.
5. **Decisions and History:** record rationale, limitations/strengths, alternatives, why alternatives were rejected, and acknowledged trade-offs. Evidence is snapshotted when the decision is saved. Link successor approaches to the run and limitation that motivated them. A single current Selected candidate is allowed per investigation; supersede the previous selection explicitly.
6. **Registry:** register a Selected, completed, evaluated candidate using a new semantic version such as `v1.0.0`. Versions cannot be overwritten. Registration freezes the checkpoint hash, source configuration, environment/source hashes, split metadata, decision, and investigation history.
7. **Inference:** compare completed run checkpoints on one PNG/JPEG image (up to 5 MB and 16 megapixels), optionally supplying its true class to see which prediction matches. Each run uses its recorded preprocessing and a checksum-verified best checkpoint. This is a single-image correctness check, not dataset accuracy; the Compare page shows validation accuracy. Separately, activate a registered version for version-bound serving predictions. Missing or changed checkpoints produce errors; there is no random-weight fallback.

## Viva notebook and model architecture controls

Open [`notebooks/TrainTrace_Viva_and_Inspection.ipynb`](notebooks/TrainTrace_Viva_and_Inspection.ipynb) in JupyterLab or VS Code with the Jupyter extension. Use it as the pipeline analysis stage: choose a run and display its actual epoch metrics, holdout evaluation, confusion matrix, configuration and checkpoint tensor shapes. Epoch metrics are available in SQLite and the readable CSV is refreshed after each completed epoch, including for runs later stopped or failed. The worker currently writes metrics to SQLite/CSV and holdout results to JSON; `.pt` files are model checkpoints, and the current code does not generate metric `.pkl` files. Training still goes through the app's durable queue so notebook analysis remains tied to the recorded run. Point `TRAINTRACE_STORAGE_DIR` at the same storage directory used by the app when using a non-default location.

To launch it from the activated project environment, install JupyterLab once with `python -m pip install jupyterlab`, then run `jupyter lab notebooks/TrainTrace_Viva_and_Inspection.ipynb`. Select the same Python environment as the app and start the API at least once so database migrations have run.

The per-run notebook export embeds the recorded model source, shared dataset/preprocessing contract, and run settings so it can train separately in Jupyter or Colab. It does not stream live results back to TrainTrace. Runs initialized from another checkpoint require those original weights and cannot be exported as a standalone reproduction; the API reports this explicitly.

For the CustomCNN family, the Training screen exposes convolution-block depth (2–6), starting channel width (8–128), classifier width, and dropout. The selected architecture profile is validated by the API and saved in run configuration/checkpoints, then reused during model registration and inference. Preset ResNet-18, MobileNetV2 and EfficientNet-B0 retain their fixed backbone layouts.

Decision reports download as Markdown. Epoch logs download as CSV; evaluation, split and audit evidence download as JSON; checkpoints download as `.pt`. Load checkpoint files only from trusted origins.

### Kaggle execution limit

The backend verifies Kaggle credentials before queuing a cloud run. TrainTrace reads Kaggle status and log markers to show progress, then downloads recorded outputs when the remote kernel completes. The installed Kaggle SDK does not provide a kernel stop operation: stopping TrainTrace monitoring can leave the Kaggle kernel running. Stop that kernel on Kaggle if needed. If status cannot be confirmed for the configured grace period, TrainTrace reports a connection error; it does not claim the remote kernel stopped. A complete real Kaggle launch through inference still needs acceptance verification.

## Configuration

| Variable | Purpose |
|---|---|
| `TRAINTRACE_STORAGE_DIR` | Managed storage root; default `backend/storage` |
| `TRAINTRACE_DATA_DIR` | Dataset cache; default `<storage>/data` |
| `TRAINTRACE_DEVICE` | `cpu`, `cuda`, or `mps`; automatic hardware selection when unset |
| `TRAINTRACE_CPU_THREADS` | Worker PyTorch thread count; default `4` |
| `TRAINTRACE_WORKER=0` | Disable automatic worker startup for isolated API testing |

Use separate storage for validation, for example:

```sh
TRAINTRACE_STORAGE_DIR=/tmp/traintrace-validation \
TRAINTRACE_DATA_DIR="$PWD/backend/storage/data" \
TRAINTRACE_DEVICE=cpu \
.venv/bin/python -m uvicorn api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The split seed identifies the 45k/5k partition. Initialization seeds control model initialization and training randomness; they do not silently alter the evaluation partition. Exact repeatability is asserted only when captured code, device, environment, data and measurements match. GPU determinism is not established by the CPU acceptance study; unsupported deterministic operations fail visibly.

## Storage, migrations and recovery

SQLite schema changes are additive. A pre-migration database copy is created for legacy schema version zero. The exact clean-install macOS/Python 3.13 dependency snapshot is in `backend/requirements-lock-macos-py313.txt`; use the portable requirements files for other supported environments.

A full source/checkpoint backup from before the repair is retained locally under `backups/` (ignored by Git).

Existing experiments, decisions, and checkpoint files are preserved. Unknown legacy provenance remains unknown; new evidence must be established by new runs. Legacy registry entries without frozen manifests cannot be activated as verified models.

Jobs are queued durably in SQLite. One worker holds an OS file lock and atomically claims one job. Cancellation is checked at batch/evaluation boundaries. On worker restart, interrupted executions become FAILED with retained metrics/artifacts; pending durable jobs remain queued. Automatic checkpoint resume is not implemented. If a worker exits unexpectedly, restart the API to recreate it and reconcile state. The UI reports worker availability.

Checkpoints are written atomically. Registry versions are stored under generated internal IDs, with name/version collision checks and transactional metadata publication. Do not manually edit or move managed artifacts.

## Verify changes

```sh
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
.venv/bin/python -m pytest --cov --cov-report=term-missing
```

```sh
cd frontend
npm test
npm run format:check
npm run build
```

CI runs these checks on pushes and pull requests. Fast tests use a small deterministic synthetic fixture, including complete training → decision → registration → activation → prediction flows. Coverage excludes the tests themselves and fails below 80%.

For an explicit real-data acceptance study, start a temporary-storage API, complete a one-epoch CIFAR-10 run in the UI, then run:

```sh
.venv/bin/python scripts/verify_real_audits.py \
  --run-id YOUR_ACCEPTANCE_RUN_ID \
  --output /tmp/traintrace-real-acceptance.json
```

This starts two replay runs and a five-seed study using the source run's complete configuration. It consumes real compute and may take several minutes.

## Architecture

- `backend/domain.py`: validated request contracts and safe identifiers.
- `backend/api/`: HTTP boundary, investigation/reporting, run monitoring, registry and serving.
- `backend/jobs.py`, `backend/worker.py`: durable admission, single-process scheduling, stop and restart handling.
- `backend/core/dataset_contract.py`: the five dataset identities and preprocessing contract used by local training and embedded in generated Kaggle scripts.
- `backend/core/`: DataLoader transforms, four model factories, explicit autograd training and checkpoint lifecycle.
- `backend/tracking/`: local coordinator, dataset preparation, durable progress, readable CSV, optional W&B, environment/source capture, and evaluation measurements.
- `backend/cloud/`: Kaggle credentials, kernel submission, remote status/telemetry, and artifact ingestion.
- `backend/services/inference_runtime.py`, `backend/services/inference_provenance.py`: upload/model execution and recorded dataset/checkpoint validation.
- `backend/db/database.py`: SQLite connections, schema migration and integrity constraints.
- `backend/storage.py`, `backend/registry/`: managed artifacts, checksums and frozen model manifests.
- `frontend/src/screens/`: workflow screens that compose smaller feature modules.
- `frontend/src/features/`: training charts/forms, comparison filters/table, and checkpoint inference controls/results.
- `frontend/src/app/useLiveRun.js`: selected-run polling and persisted live sample state.
- `frontend/src/components/`: shared accessible inputs/panels and metric charts.
- `frontend/src/app/useWorkspace.js`: shared selection, catalog refresh, and workspace actions.

## Status and remaining scope

See [the repair status and evidence](docs/audits/2026-10-15/REPAIR_STATUS.md) and [the original audit](docs/audits/2026-10-15/PROJECT_AUDIT_AND_REPAIR_PLAN.md). The audit is a historical record of the pre-repair code; its probe script intentionally describes that old implementation.

The local pipeline, optional Kaggle adapter, comparison, inference, and reports are implemented at different verification levels. See [the MVP refactor plan](docs/architecture/MVP_REFACTOR_PLAN.md) for remaining cloud, browser, migration, and cross-runner checks. Passing local tests does not establish that a real Kaggle job or every UI state works end to end.
