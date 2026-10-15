# TrainTrace repair status and handover

**Core repair phases 0–6: complete for the local CIFAR-10 baseline.**  
**Phase 7: optional expansion remains.**  
**Revised PRD completion estimate: 84/100**, up from the initial 43/100. This is a weighted engineering assessment (approximately ±5), not a measured percentage of hours or a claim that every PRD requirement is satisfied.

## Phase completion

| Phase | Status | Delivered |
|---|---|---|
| 0 — Preserve evidence and establish baseline | Complete | Source/checkpoint archive, consistent SQLite backup, checksum manifest, explicit local single-user/CIFAR-10 scope |
| 1 — Contracts and evidence integrity | Complete | Validated decision/promotion contracts, truthful empty/offline/error states, no fabricated evidence, safe managed paths, missing-checkpoint errors, immutable versions |
| 2 — Durable execution and evaluation | Complete | One worker process/file lock, durable queue and cancellation, restart reconciliation, per-epoch metrics/LR, best/last/periodic checkpoints, checkpoint-linked holdout metrics |
| 3 — Reproducibility and comparison | Complete | Full-config replay, independent split/initialization seeds, exact trajectory checks, five-seed stored statistics, selected-run chart overlays and measured comparison data |
| 4 — Investigation and model lifecycle | Complete for baseline | Editable/archiveable investigations, durable predecessor/limitation links, structured append-only decisions with evidence snapshots, frozen lineage, separate registration/activation, registered-version inference, decision report |
| 5 — UI workflows | Complete for baseline | Eight modular screens, explicit investigation/run selectors, charts/tables, artifact downloads, live progress, persistent selection, responsive layouts, associated labels, keyboard controls and visible focus |
| 6 — Verification and delivery | Complete locally | Clean Python/frontend installation checks, automated tests/coverage, connected real-data/browser acceptance, migration/integrity checks, latency sample, CI configuration, corrected documentation |
| 7 — Extensions | Not started | Additional datasets, W&B, multi-user sessions, richer search/tagging, graphical investigation exploration, PDF/image exports |

“Complete for baseline” means the repaired local core is implemented and checked. Remaining PRD breadth and unverified guarantees are itemized below rather than hidden behind a blanket completed status.

## Verification results

- **Backend:** 34 tests passed with **92.96% line coverage**, excluding test files. The ≥80% gate passes. Tests include queue admission, invalid contracts, zero seeds, preserved epochs after failure, stop/restart handling, model compatibility, split independence, schedules, version collisions, frozen decisions, checksums, and actual registered-model predictions.
- **Clean environment:** installed the pinned backend requirements in a fresh Python 3.13 virtual environment, `pip check` reported no broken requirements, and all 34 tests passed there with the same coverage. A transitive macOS/Python 3.13 snapshot is in `backend/requirements-lock-macos-py313.txt`.
- **Frontend:** clean `npm ci`, four API-client tests, formatting check, and production build passed. Vite was upgraded to 8.3.4 with its compatible React plugin; npm's installation audit reported **zero known vulnerabilities**.
- **Code checks:** Ruff lint/format and `git diff --check` passed. CI now runs backend lint/format/tests/coverage and frontend tests/format/build. The remote GitHub workflow itself has not been executed in this session.
- **Legacy preservation:** a migration rehearsal on a copy retained all 6 experiments, 8 runs, 32 epoch metrics, 5 decisions and 1 model. All **13 original checkpoint SHA256 hashes remained unchanged**. Acceptance runs used temporary storage, not the user's original database.
- **Real CIFAR-10:** final-source CustomCNN, 1 epoch, batch 256, AdamW, LR 0.001, initialization seed 42, split seed 42. Validation accuracy **57.88%**, holdout accuracy **57.40%**, test loss approximately **1.1818**. This is a pipeline acceptance workload, not a model-quality benchmark.
- **Protocol A:** two full-config replay runs matched the original exact numerical metric trajectory, test loss and accuracy, source/environment, and dataset snapshot. Accuracy difference **0.0**. Epoch durations are deliberately excluded from equality.
- **Protocol B:** five controlled seeds on the same split, with matching recorded environments. Mean test accuracy **56.292%**; population standard deviation **1.259228 pp**; minimum **54.75%**, maximum **58.00%**, spread **3.25 pp**.
- **Alternative investigation:** a one-epoch SGD successor linked to the earlier baseline completed with **39.80%** holdout accuracy. Its rejection record explicitly limits the conclusion to this acceptance configuration. This does not establish general optimizer superiority.
- **Browser lifecycle:** created an investigation; launched real training; selected comparison curves; saved supersession/rejection/selection reasoning; created a linked successor; registered `CIFAR10-Acceptance:v1.0.0`; activated it; uploaded a cached holdout image; and downloaded the decision report. Reload retained the investigation, selected run and saved history.
- **Browser inference:** the registered model predicted **cat, 67.06% confidence**, for the first CIFAR-10 test image (true class cat), and displayed version `v1.0.0` and originating run `cifar_acceptance_02`. One observed inference response was **44.81 ms**; this is not a latency distribution or throughput claim.
- **UI states:** inspected 1366×768 and 1920×1080 layouts; no document-level horizontal overflow was found in the measured laptop history view (1351 px document width at a 1366 px viewport). Wide comparison tables scroll inside their containers. Keyboard Tab reached the visible skip-to-content link. Stopping the API produced an explicit offline state instead of fake compute/serving success.
- **Local HTTP sample:** 20 requests per endpoint on the acceptance database. P95 listing latency was approximately **1.17 ms**, comparison **8.17 ms**, registry **1.22 ms**, all below the PRD's 300 ms local query target for this small sample. This is not a load test.

The user-triggered interruption during the first five-seed study stopped the background processes. Recovery marked that audit failed and preserved its participating run; a new complete study passed afterward. Interrupted records were retained as evidence of recovery behavior.

## What changed

### Pipeline and persistence

The API now enqueues immutable run configurations before acknowledging a launch. A single local worker claims jobs transactionally, with an OS lock preventing a second worker from executing the same queue. Training, audits and cancellation share the same scheduling policy. Restart reconciliation marks interrupted executions failed and retains evidence; queued jobs remain durable.

Each epoch commits metrics immediately, including the actual learning rate. Best and last checkpoints are atomic, with periodic checkpoints every five epochs. The best validation checkpoint is evaluated on the holdout test set before a run becomes completed. Precision, recall, F1, confusion data, parameter count, artifact size and latency methodology are captured.

The schema migration adds configuration/environment/dataset/evaluation fields and structured jobs, events, audits, artifacts, decisions and serving state. New duplicate epoch inserts and duplicate model versions are rejected. Legacy facts are not synthesized.

### Scientific evidence and governance

Python, NumPy, PyTorch and worker RNG controls are initialized centrally, with deterministic algorithm policy. Dataset splitting has a distinct seed and stored indices/hash. Protocols replay the original configuration, create unique child runs, and persist their evidence. A report flags mismatched execution environments rather than asserting repeatability.

Decision submissions require valid status, nonempty rationale, limitations, alternatives and trade-offs, and a completed evaluation. Decisions are append-only and freeze current evidence. Selected models cannot be registered without intact evaluated weights and captured provenance. Registration snapshots the investigation history and source metadata; repeated versions cannot overwrite weights or lineage. Activation verifies checkpoint structure and identity separately.

Inference resolves the explicitly active registered version and verifies its checksum. It reconstructs preprocessing from the frozen manifest, limits image inputs, returns model/run/version metadata, and never silently predicts from random weights.

### UI and code organization

The former phase-only interface was replaced with persistent workspace navigation and separate screen modules. Users can reopen historical runs, compare up to four candidates, inspect audits, preserve decisions, branch investigations, inspect frozen registry history, activate a version and test inference. Errors include backend validation details. Unknown and offline states are explicit. Numeric example evidence and invented historical transcripts were removed.

The local plain-CSS light theme remains the implementation choice. The user-facing behavior and accessibility take priority over adopting Tailwind solely because it appears in the PRD's proposed stack. Backend HTTP, scheduling, training/evaluation, persistence, artifact handling and registry responsibilities are separated. The unused legacy CRUD module was removed after callers moved to the transactional persistence boundary.

## Finding closure map

| Audit finding | Disposition |
|---|---|
| F01 decision request mismatch | Fixed; browser and contract tests pass |
| F02 promotion response mismatch | Fixed; registration and lineage browser flow pass |
| F03 random/unregistered inference | Fixed; missing/modified/incorrect version requests fail |
| F04 invalid/mutable registry releases | Fixed; selected/evaluated requirements and immutable collision tests |
| F05 fabricated evidence/current-device provenance | Fixed for new records; legacy unknowns remain labeled |
| F06 unsafe path identifiers | Fixed with constrained identifiers and managed path containment |
| F07 concurrent/reused execution | Fixed for local single-worker scope; restart API after unexpected worker exit |
| F08 delayed metrics/LR persistence | Fixed; completed epoch evidence survives injected failure |
| F09 checkpoint lifecycle | Fixed for best/last/periodic artifacts; automatic resume remains outside baseline |
| F10 disconnected holdout evaluation | Fixed; real holdout and secondary metrics recorded |
| F11–13 misleading reproducibility | Fixed and verified on CPU; GPU assurance remains unverified |
| F14–15 missing investigation/decision domain | Core fixed; predecessor links, structured history and evidence persist. Rich graph UI and explicit cross-entity alternative linking remain improvements |
| F16 misleading comparison | Fixed core measurements/overlays/selection; configuration details are expandable rather than a full pivoted parameter grid |
| F17 wrong run/phase/completion state | Fixed explicit run identity, refresh and authoritative state handling |
| F18 preprocessing/serving contract | Fixed version-bound preprocessing, input limits, metadata and controlled model cache |
| F19 validation/transactions/migrations | Core fixed; full generated response-client types remain an improvement |
| F20 artifacts/reporting | Core downloads/CSV/JSON/Markdown report implemented; PDF and image exports remain |
| F21 accessibility/responsiveness | Concrete controls/layout/contrast/focus improvements and viewport checks complete; full WCAG certification is not claimed |
| F22 false status/poor errors | Fixed offline/error handling and persisted events; no invented logs |
| F23 missing tests/setup | Fixed local tests, coverage, clean installation, locks and CI configuration |
| F24 inaccurate documentation | Corrected READMEs, actual parameter counts, commands, units and limitations |
| F25 scope contradictions/secondary features | Explicit local core baseline; expanded datasets/W&B/auth/tagging and richer discovery deferred |

## Revised score

| Area | Earned / available |
|---|---:|
| Data, models and autograd | 14 / 15 |
| Execution and durable tracking | 9 / 10 |
| Evaluation and comparison | 8 / 10 |
| Investigation and decision traceability | 15 / 20 |
| Reproducibility | 9 / 10 |
| Registry, lineage and serving | 9 / 10 |
| UI/workflow | 8 / 10 |
| API/persistence/architecture | 8 / 10 |
| Verification/delivery | 4 / 5 |
| **Total** | **84 / 100** |

The remaining score reflects PRD breadth and evidence limits, not unresolved copies of the original blocking contract/data-integrity bugs.

## Remaining work and limits

1. **Phase 7 scope:** expanded datasets, W&B, multi-user auth/ownership/sessions, tags and richer global filtering, graphical history exploration, PDF decision reports and confusion-matrix image exports.
2. **Broader assurance:** GPU/MPS/CUDA repeatability and failure handling, Windows support (worker locking currently uses POSIX `fcntl`), a full accessibility audit, larger database/load tests, complete browser automation in CI, and remote CI execution.
3. **Timing guarantees:** live metrics poll at 400 ms while the training view is open; this is not a measured guarantee of <500 ms event-to-render latency. Epoch metrics exist only after an epoch completes, so the PRD's universal first-metric-within-30-seconds criterion must be workload-qualified. CPU acceptance epochs took roughly 30–40 seconds.
4. **Runtime boundaries:** restart the API after backend source changes; worker modules are not hot-reloaded. Restart also reconciles unexpected worker exits. No automatic checkpoint resume, public hosting, distributed training or enterprise queue infrastructure is included.
5. **Legacy records:** historical missing provenance cannot be reconstructed truthfully. Original candidates remain inspectable, but a fresh verified run is needed before registering/activating one as a new trustworthy version.
6. **Model quality:** the one-epoch studies demonstrate pipeline behavior. A proper research conclusion needs longer runs, appropriately designed experiments and independent model-quality evaluation.

## Evidence files

- `POST_REPAIR_TESTS.txt`, `CLEAN_INSTALL_TESTS.txt`, `COVERAGE.json`
- `FRONTEND_CHECKS.txt`
- `INTEGRITY_AND_MIGRATION.json`
- `REAL_CIFAR_ACCEPTANCE.json` (original and both completed audit reports)
- `FINAL_LIFECYCLE.json` (decisions, predecessor links, registered frozen manifest and serving pointer)
- `HTTP_PERFORMANCE.json`
- `EXPORTED_DECISION_REPORT.md`
- `INFERENCE_VERIFIED.jpg`, `HISTORY_LAPTOP.jpg`, `OFFLINE_STATE.jpg`

Full pre-repair source/checkpoint backup: `backups/20261015-233220/`. The acceptance database/artifacts are in `/private/tmp/ttp-connected-validation/`; the original application database was not used for acceptance writes. Temporary verification servers were stopped after checks. Use the repository README to start the application against its normal managed storage.

No commit, push, pull request or deployment was performed. Existing uncommitted work is preserved in the pre-repair backup, and the final changes remain available for review in the working tree.
