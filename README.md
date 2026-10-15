# TrainTrace — Tracked Training Pipeline

TrainTrace is a local ML investigation workspace. It connects seeded PyTorch training, holdout evaluation, reproducibility studies, candidate comparisons, human decision history, immutable model versions, and version-bound inference.

The supported core is **CIFAR-10 on a single-user macOS/Linux workstation**, with one compute job at a time. Additional datasets, W&B synchronization, multi-user authentication, and PDF/image report exports remain extensions. The original product specification is in [docs/PRD](docs/PRD/Tracked_Training_Pipeline_PRD.md); the implementation baseline and current limitations are documented below.

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

CIFAR-10 downloads on first use, then works from its cache. ImageNet initialization also requires a first-use download. Existing cached datasets can be reused with `TRAINTRACE_DATA_DIR`. No cloud account is required.

## Workflow

1. **Investigations:** define an objective, hypothesis, and optional accuracy/latency targets. Targets and all accuracy measurements use **0–100 percent**. Edit conclusions and archive investigations here.
2. **Training:** configure an architecture, optimizer, schedule, initialization seed, and independent split seed. Queue a unique run ID. Completed epoch metrics persist immediately, and best/last/periodic checkpoints are catalogued with SHA256 checksums. A stopped or failed run retains completed evidence.
3. **Compare:** select up to four candidate runs and inspect validation trajectories, hyperparameters, measured parameter counts, holdout accuracy, checkpoint size, duration, and latency. The overfitting gap uses training and validation accuracy from the same final epoch.
4. **Audits:** Protocol A replays the original full configuration twice and compares exact numerical trajectories plus test loss/accuracy against the original. Timing is excluded. Conditions must match. Protocol B defaults to five distinct initialization seeds, holds the data split fixed, and persists per-seed test accuracies, mean, population standard deviation, minimum, maximum, and spread. Both use the same sequential queue as ordinary training.
5. **Decisions and History:** record rationale, limitations/strengths, alternatives, why alternatives were rejected, and acknowledged trade-offs. Evidence is snapshotted when the decision is saved. Link successor approaches to the run and limitation that motivated them. A single current Selected candidate is allowed per investigation; supersede the previous selection explicitly.
6. **Registry:** register a Selected, completed, evaluated candidate using a new semantic version such as `v1.0.0`. Versions cannot be overwritten. Registration freezes the checkpoint hash, source configuration, environment/source hashes, split metadata, decision, and investigation history.
7. **Inference:** activate a registered version, then upload PNG/JPEG images (up to 5 MB and 16 megapixels). Preprocessing comes from the frozen manifest. Predictions identify the model version, run, checkpoint checksum, top classes, and confidence. Missing or changed checkpoints produce errors; there is no random-weight fallback.

Decision reports download as Markdown. Epoch logs download as CSV; evaluation, split and audit evidence download as JSON; checkpoints download as `.pt`. Load checkpoint files only from trusted origins.

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
- `backend/core/`: CIFAR-10 preprocessing, four model factories, explicit autograd training and checkpoint lifecycle.
- `backend/tracking/`: per-epoch persistence, measured holdout evaluation, full-config audits, environment/source capture.
- `backend/db/database.py`: SQLite connections, schema migration and integrity constraints.
- `backend/storage.py`, `backend/registry/`: managed artifacts, checksums and frozen model manifests.
- `frontend/src/screens/`: investigation, training, comparison, audits, decisions, history, registry and inference screens.
- `frontend/src/components/`: shared accessible inputs/panels and metric charts.
- `frontend/src/App.jsx`: selection, refresh coordination and workspace navigation.

## Status and remaining scope

See [the repair status and evidence](docs/audits/2026-10-15/REPAIR_STATUS.md) and [the original audit](docs/audits/2026-10-15/PROJECT_AUDIT_AND_REPAIR_PLAN.md). The audit is a historical record of the pre-repair code; its probe script intentionally describes that old implementation.

The core pipeline is implemented and tested. Expanded dataset support, W&B, multi-user sessions, tags/global cross-entity filtering, PDF reports, confusion-matrix image exports, and a fully interactive graph remain extensions. The current history view exposes predecessor relationships and decision evidence as cards. Performance, accessibility and GPU claims must be read alongside the recorded verification limits; passing tests is not proof of every PRD requirement.
