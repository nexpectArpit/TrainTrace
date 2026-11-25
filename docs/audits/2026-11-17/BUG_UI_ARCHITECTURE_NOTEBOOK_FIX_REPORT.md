# TrainTrace implementation repair report

**Date:** 2026-11-17  
**Scope:** CIFAR-100 support, CustomCNN layer controls, notebook analysis, richer search/reporting, and accessibility improvements.

## Implemented changes

### Dataset and architecture pipeline

- Added CIFAR-100 beside CIFAR-10 with dataset-specific normalization, class counts and labels, train/validation/holdout splits, source-file hashes, and run provenance.
- Model heads, evaluation confusion matrices, registry reconstruction, and inference probabilities now use the dataset's recorded class count. Audit replays carry the dataset configuration.
- Added CustomCNN controls for convolution blocks (2–6), starting width, classifier width, and dropout. Values persist through audits, checkpoint configuration, registration, and inference. The default layout preserves existing checkpoint tensor names and shapes.
- Legacy runs without a dataset field continue to resolve to CIFAR-10.

### Notebook and readable pipeline outputs

- The notebook selects a real run and displays its recorded configuration, per-epoch metrics, holdout evaluation, confusion matrix, and checkpoint tensor names/shapes.
- Training refreshes the readable metrics CSV artifact after each completed epoch. Completed metrics remain available if a run is later stopped or fails. SQLite remains the authoritative record; evaluation output is JSON and model weights are `.pt` checkpoints.
- Current code does not create metric `.pkl` files. Notebook run listing handles missing/empty databases and legacy records after the API has initialized migrations.
- Training remains submitted through the durable application queue; notebook analysis reads the same tracked records and files.

### Search and reporting

- Added filtering by dataset, architecture, optimizer, CustomCNN depth, execution/decision status, seed, validation accuracy, and holdout accuracy. Search terms include run IDs, names, architecture, dataset, and recorded configuration.
- Added investigation search to the Investigations screen.
- Expanded the Markdown report with a candidate comparison, run configuration, epoch metrics, holdout evaluation, audit reports, decisions, and registered versions.
- Added a combined CSV report with run metadata, hyperparameters, per-epoch train/validation metrics, and holdout metrics.

### Accessibility and UI fixes

- Added 44 px minimum control heights, larger checkboxes, visible keyboard focus, a focusable main landmark, reduced-motion support, live status announcements, and accessible epoch tables for comparison charts.
- Preserved responsive layouts and associated form labels.
- Fixed stale persisted run selections, progress polling through holdout evaluation, transient live-update retry behavior, and Protocol A's dependency on the unrelated Protocol B seed field.
- Stop and lineage actions are disabled when the API is offline.

## Main changed files

- Backend: `backend/domain.py`, `backend/core/dataset.py`, `backend/core/models.py`, `backend/tracking/tracker.py`, `backend/api/routers/runs.py`, `backend/api/routers/experiments.py`, `backend/api/routers/inference.py`, `backend/registry/model_registry.py`.
- Frontend: `frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/components/Common.jsx`, and the Training, Compare, Investigations, Audits, Registry, History, Decisions, and Inference screens.
- Notebook/docs: `notebooks/TrainTrace_Viva_and_Inspection.ipynb`, `README.md`, `SYSTEM_METRICS.md`, `docs/PRD/CLARIFICATIONS_2026-11-17.md`.

## Verification

- Backend: **36 tests passed**, **91.79% line coverage**, above the 80% gate; Ruff lint and formatting checks passed.
- CIFAR-100: mocked dataset loader/normalization and model-head checks passed; a synthetic 100-class train → evaluation → registration → activation → inference flow passed with a 100×100 confusion matrix and 100 prediction probabilities.
- Search/reporting: API filter and CSV/Markdown report assertions passed.
- Frontend: **4 client tests passed**, Prettier check and production build passed.
- Notebook: all 14 cells parsed and each Python cell compiled. The notebook was not executed in a Jupyter kernel because Jupyter is not installed in the project environment.
- `git diff --check` passed.
- A live browser/viewport pass could not be completed: this environment rejected binding the Vite dev server with `EPERM`. Full WCAG certification and physical screen-reader validation are not claimed.

CIFAR-100 uses synthetic fixtures for the fast test run; a full dataset download and longer real-data quality study remain outstanding. The backend test run emitted a Starlette/httpx deprecation warning from the installed TestClient dependency; it did not affect the result.

## Remaining scope

- Custom layer configuration applies to CustomCNN; ResNet-18, MobileNetV2, and EfficientNet-B0 retain fixed internal layouts.
- CIFAR-100 has synthetic loader and end-to-end lifecycle coverage; real-data quality and runtime still need a separate study.
- W&B, multi-user sessions, tags, PDF/image exports, a fully interactive investigation graph, GPU/Windows assurance, and large-scale load testing remain outside this implementation.
