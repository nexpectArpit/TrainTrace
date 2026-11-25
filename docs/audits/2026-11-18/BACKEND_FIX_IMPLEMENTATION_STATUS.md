# Backend and pipeline fix status

**Updated:** 2026-11-18  
**Scope:** fixes applied after the static backend/MLflow review in `BACKEND_ARCHITECTURE_AND_MLFLOW_REVIEW.md`.

## Implemented

- Candidate training and comparisons use train/validation data only. A selected candidate can consume one final test evaluation per investigation. The API reserves that evaluation transactionally, freezes decisions, and records failure or stop states. The Decisions screen now follows this sequence.
- Existing databases retain old `evaluation_json` as **historical test exposure**, not as a valid final evaluation. Such runs cannot be registered as newly evaluated candidates; old leakage cannot be undone.
- Added CIFAR-10/100, MNIST, Fashion-MNIST, and SVHN loader support. Dataset metadata captures class names, counts, split, source-file hashes, transforms and initialization. Pretrained inputs use 224px ImageNet normalization; scratch models use 32px dataset normalization. ResNet pretrained stem is preserved and restored for final evaluation, registry activation and inference without redownloading ImageNet weights.
- Added optional checkpoint warm-start from a finished run in the same investigation. The checkpoint hash, model, architecture and class count are checked; optimizer and scheduler restart from their initial state. This is a fork, not an exact continuation.
- Replaced direct `fcntl` calls with a cross-platform process-lock helper.
- Queue/reject admission now checks queued and running jobs under the admission transaction. Stop requests use conditional state transitions and the worker resolves cancellation against the persisted completion state.
- Added ordered SQLite migrations for validation/final-evaluation separation, tags, one final-evaluation reservation per investigation, and storage-relative artifact/registry keys. A pre-migration database backup is made for the baseline upgrade.
- Added server-side run filters and bounded pagination to comparisons. Added exact tag search across runs, investigations and registered models.
- Final evaluation now records test metrics separately and reports model-only batch-one p50/p95 latency with warmups and device synchronization. Registry latency uses p50; comparison no longer labels a data-loader throughput estimate as inference latency.
- CSV and Markdown reports use validation metrics for candidate selection and include final test metrics only when present. Decision evidence snapshots include configuration, environment, dataset, checkpoint hash, epoch trajectory and completed audits.
- The frontend dev server proxies `/api` to FastAPI, so the earlier claim that Vite's fallback port necessarily causes a CORS failure was incorrect. No permissive CORS policy was added.

## Remaining limits

- Router, service, repository and artifact-store responsibilities remain coupled in several modules. This pass introduced service/repository boundaries around run lookup, search, and decision transactions, but did not split every existing router operation into a clean domain architecture.
- Exact replay may still vary across hardware and library versions. The state hash compares saved model weights exactly; Protocol B confidence intervals with five seeds are descriptive and should not be presented as strong population estimates.
- W&B synchronization was validated only for graceful optional integration paths, not against an authenticated W&B workspace. The project does not include a credentialed integration run.
- Hands-on accessibility review and cross-browser visual review remain outstanding. The lineage graph supports keyboard operation in markup but has not had a screen-reader audit.
- The test partition is reserved once per investigation, including when evaluation fails or is stopped. This avoids repeated peeking but means a failure after the test pass starts requires a new investigation and untouched test data for a new final claim.

## Validation

No full training benchmark or external dataset download was run. Latest checks: backend lifecycle suite **38 passed**; frontend service suite **4 passed**; frontend production build passed; Ruff passed; Python compileall passed; `git diff --check` passed. Hardware-specific replay parity, authenticated W&B synchronization, and hands-on accessibility review remain unverified.
