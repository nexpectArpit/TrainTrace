# TrainTrace project audit and phased repair plan

**Date:** 15 October 2026  
**Status:** Analysis complete; implementation awaits owner review and approval.  
**Baseline:** PRD v5.2, current working tree (including uncommitted changes), latest commit `7a53b4d`.  
**Overall assessment: 43/100 — substantial prototype, incomplete core product workflows.**

## 1. What we are actually building

TrainTrace is a local, evidence-based ML investigation and model lifecycle application. Its defining feature is preserving the reasoning behind model choices, supported by reproducible training and trustworthy measurements. A training dashboard alone does not satisfy the product.

The essential chain is:

**Objective → Approach → Runs → Evidence → Limitations → Decision → Reason → Alternatives → Why alternatives were rejected → Next investigation → Final selected approach.**

A reviewer must be able to start with an inference model version and trace its actual weights to the exact run, configuration, dataset split, environment, evaluation evidence, and human decision. Rejected and superseded attempts must remain understandable. Selection belongs to the human; the platform preserves the evidence.

The practical scope is a solo-developer, local React/FastAPI/PyTorch application with SQLite, CIFAR-10, one active training job, reproducibility protocols, comparison, structured decisions, versioned registration, and inference. Enterprise orchestration, Kubernetes, distributed training, and automatic architecture selection are unnecessary for this recovery.

## 2. Completion rating and interpretation

This is an engineering estimate of implemented PRD behavior, not a measured percentage of development hours. Partial code earns partial credit; missing integration, evidence integrity, and unverified behavior reduce credit. Uncertainty is roughly ±5 points. No percentage implies release approval.

| Area | Available points | Earned | Assessment |
|---|---:|---:|---|
| CIFAR-10, models, autograd training | 15 | 11 | Real loaders, four model factories, optimizer, validation, best checkpoint; incomplete configuration and checkpoint lifecycle |
| Execution and durable tracking | 10 | 4 | Background execution and progress exist; no single-job guard, cancellation, recovery, or per-epoch persistence during execution |
| Evaluation and comparison | 10 | 3 | Validation summaries and comparison table exist; holdout evaluator disconnected, richer metrics and curve comparisons absent |
| Investigation and decision traceability | 20 | 6 | Experiment/run records and rationale storage exist; UI submission broken, reasoning structure and durable branching absent |
| Reproducibility | 10 | 3 | Seeded PyTorch and audit routines exist; audits do not replay the actual run or preserve defensible reports |
| Registry, lineage, serving | 10 | 4 | Registry copies files and prediction endpoint performs real inference; provenance and lifecycle guarantees fail |
| UI and workflow | 10 | 5 | Modular four-phase interface builds and renders; selection, recovery, truthfulness, navigation, and accessibility need work |
| API, persistence, architecture | 10 | 5 | Useful module boundaries and SQLite foreign keys/WAL; weak validation, contracts, state management, and migrations |
| Verification and delivery | 5 | 2 | Readable docs and successful build; no implemented automated tests, no demonstrated coverage/acceptance suite |
| **Total** | **100** | **43** | **Prototype, not a completed MVP** |

Your estimate of approximately 60% is plausible for visible feature scaffolding. I would not call it 60% complete against the promised product behavior: the critical decision-to-registry-to-inference chain is broken, and several displayed claims exceed the available evidence. Roughly 57 weighted acceptance points remain, but they are not 57% of calendar effort.

**Recommendation:** retain the useful foundation and repair the lifecycle end to end. A wholesale rewrite would discard working training/data code without resolving the product contracts by itself.

## 3. Inspection and verification performed

- Read both Markdown PRD copies; they are byte-identical. Reviewed README, system metrics, all 21 backend Python files, frontend application/components/service/CSS, dependency manifests, and Vite configuration.
- Inspected current Git status. Existing source changes were already present; this audit did not implement application fixes or overwrite them.
- Frontend production build passed: `npm run build -- --outDir /private/tmp/ttp-audit-build`, Vite 4.5.14, 37 modules transformed.
- Python syntax parsing passed for all 21 backend files.
- Ran isolated probes using Homebrew Python 3.13, with database and artifacts redirected to temporary directories. Confirmed decision schema rejection, invalid-input acceptance, discarded motivation, invalid promotion, version collision, missing-checkpoint inference, model parameter count, and missing resize.
- Ran a small synthetic CPU training smoke check; see `VERIFICATION_RESULTS.txt`. This is a basic engine check, not CIFAR-10 accuracy or reproducibility validation.
- Inspected the rendered frontend in the browser with the backend intentionally not running. Confirmed misleading online/running/serving labels and populated example evidence despite zero loaded runs. No training or registry action was submitted in the browser.
- Read existing SQLite storage in read-only mode: 6 experiments, 8 runs, 32 epoch metric rows, 5 decisions, 1 model. Run states: 6 COMPLETED, 1 QUEUED, 1 RUNNING. Found 13 `.pt` files and a nonempty dataset cache. These establish previous activity, not correctness or accuracy. No backend listener was found during initial inspection; persisted active states need reconciliation, not automatic deletion.
- `backend/tests` contains only an empty `__init__.py`; frontend has no test script. No existing coverage report or CI configuration was found.

**Limits:** no full CIFAR-10 benchmark, two-run determinism study, five-seed study, complete HTTP end-to-end suite, performance benchmark, or complete viewport/accessibility audit was executed. The UI inspection covers empty/disconnected behavior; successful connected workflows were assessed through source contracts and isolated backend probes. No dependency installation was performed. The default Python lacks FastAPI/torchvision; Homebrew Python has them but lacks pytest/httpx. Reproducibility and performance claims therefore remain unverified.

## 4. Prioritized findings

Priorities: **P0** means integrity or core-workflow blocker before trusting the product; **P1** means required MVP functionality/reliability; **P2** means usability, reporting, delivery, or staged enhancements. These are grouped repair items, not an exhaustive count of individual defects.

### P0 — six blocking repair groups

**F01 — Decision submission fails at the UI/API boundary.**
`frontend/src/components/Phase4_Decision.jsx:52` sends `decision_rationale`; `backend/api/routers/experiments.py:28` requires `rationale`. The isolated schema check rejected the actual field shape with missing `rationale`; FastAPI validation would reject that request. Evidence/trade-off fields also have no matching backend storage. Fix the shared contract and round-trip all structured evidence; test real UI-shaped requests.

**F02 — Registry promotion succeeds but the frontend interprets it as failure.**
`Phase4_Decision.jsx:92` expects `res.model`, then uses `res.model.id`; `backend/api/routers/registry.py` returns `details` containing `model_id`. Thus registration can mutate state before the UI throws. Fix the response contract, show the persisted result, and make retries safe. Add an integration test covering promotion followed by lineage retrieval.

**F03 — Predictions can come from random, unregistered weights.**
`backend/api/routers/inference.py:53` does not reject a missing checkpoint. With no run ID it searches arbitrary artifact files and swallows loading errors. A temporary 32×32 image and nonexistent run returned a class/confidence from an untrained model. Inference does not resolve a promoted registry version. Require a valid serving model ID, verified checkpoint and preprocessing metadata; fail explicitly if unavailable. Never substitute random weights.

**F04 — Registry permits invalid releases and can corrupt provenance.**
`backend/registry/model_registry.py:51` permits nonexistent checkpoint paths and checks neither completed execution nor a Selected decision. Caller-supplied test metrics are trusted. Files are copied before an upsert whose conflict update retains the original `run_id`. An isolated test registered run A, reused name/version for run B, and observed run A metadata pointing to run B bytes. Require evaluated/Selected candidates; derive metrics from stored evaluations; enforce immutable unique name/version; stage and hash files; coordinate file publication with the database transaction. Separate registration from activation for inference.

**F05 — Displayed evidence and provenance are not reliably factual.**
`Phase4_Decision.jsx:15` prepopulates specific accuracy, alternative results, and audit-success claims regardless of actual evidence. It also includes a fallback `66.14` accuracy. Lineage labels claim audited/unbroken history while only showing a small summary. `model_registry.py:134` reports current hardware and hard-coded dataset text rather than historical run snapshots. Remove factual sample values from editable records, distinguish unknown/unverified from measured, and freeze actual evidence/provenance at decision and registration time.

**F06 — User IDs are used as filesystem paths without containment checks.**
Launch/run/model identifiers and versions are free strings used in checkpoint paths in `trainer.py`, `model_registry.py`, and `inference.py`. A `../outside` run ID passes launch validation. Static inspection shows potential reads/writes outside artifact roots when paths resolve; no exploit against user files was attempted. Generate opaque internal IDs, validate display names separately, and verify resolved paths stay within managed storage. Include traversal and collision tests.

### P1 — thirteen MVP repair groups

**F07 — No reliable job coordinator.**
`runs.py:75` schedules in-process background tasks with no admission lock or durable queued record before acceptance. Audits execute synchronously in their request handlers, outside any common queue. Concurrent jobs share process RNGs/resources. Existing run IDs are reused by `tracker.py` without validating configuration, allowing overwritten checkpoints and appended duplicate metrics. Introduce a single local worker process and durable queue, unique immutable runs, idempotent launch, cancellation, failure capture, and startup reconciliation. No external queue service is necessary initially.

**F08 — Metrics persist only after the entire run completes.**
`tracker.py:156–176` calls `trainer.train()` before saving epoch metrics. Completed epochs can be lost if a later epoch fails; live metric tables stay empty while training. Learning rate is not stored per epoch; progress displays initial LR even with a scheduler. Persist metrics after each epoch, with `(run_id, epoch)` uniqueness, actual LR, durable events, bounded log retrieval, and recovery tests.

**F09 — Checkpoint lifecycle is incomplete.**
`trainer.py:189–256` only saves on validation improvement; best starts at zero, so zero accuracy can produce no checkpoint. There is no periodic/final guarantee, artifact catalog, or complete configuration/RNG/scheduler snapshot. Add best, last, and periodic artifacts, atomic writes, checksums and manifests; preserve valid artifacts when stopped/failed. Resume can remain optional unless explicitly added to scope.

**F10 — Holdout evaluation is not integrated.**
`tracker.py` discards the test loader and marks COMPLETED after validation. `Evaluator.evaluate_holdout()` exists but has no caller in the training lifecycle/API. The evaluation screen promises holdout analysis while showing validation metrics. Persist evaluation against a specific checkpoint before marking the candidate evaluated; record test loss/accuracy, latency methodology, parameter count, and precision/recall/F1/confusion data as required. Never relabel validation as test evidence.

**F11 — Protocol A does not prove the promised repeatability.**
`evaluator.py:68–87` trains two fresh default configurations and compares only best validation accuracy within 0.01 percentage points. It does not load the originating run's full configuration, compare full trajectories/test accuracy, or enforce environment parity. The UI forces one epoch and changes seed 0 to 42 through `||`. Resolve immutable source configuration; define exact versus tolerance-based checks honestly; compare metric trajectories excluding nondeterministic timing, test results, and relevant hashes; persist an audit with participating run IDs and mismatch reasons.

**F12 — Protocol B changes more than initialization and loses results.**
`evaluator.py:94–119` defaults to three seeds, evaluates best validation accuracy, omits explicit min/max, and writes reusable `prob_b_seed_*` filenames. Changing the same seed also changes train/validation split in `dataset.py:116`, confounding initialization sensitivity with split changes. UI forces one epoch; results disappear on unmount and are not attached to the investigation. Use five controlled seeds by default, fixed split identity, original configuration, unique audit child runs, stored per-seed test accuracy, mean/std/min/max/spread and sample-count/statistical convention. Validate empty/duplicate seeds. Keep any split-sensitivity mode separately named.

**F13 — Determinism metadata and controls are incomplete.**
Only PyTorch/CUDA seeding is explicit. Python/NumPy seed setup, explicit worker seeding, deterministic algorithm policy, DataLoader RNG handling, and environment snapshots are absent. Centralize the protocol before model construction; record supported device/environment conditions and reasons exact repeatability cannot be asserted. Concurrent global RNG use must be eliminated through F07.

**F14 — The investigation domain is missing key relationships.**
`db/database.py` stores experiment objective/targets but no hypothesis, conclusion, archive state, predecessor limitation, or investigation edges. `motivating_reason` is sent by the frontend but discarded by `LaunchRunSchema`; the probe confirmed this. Branching only prefills a form. Add structured investigation and approach relationships with real predecessor/limitation IDs and durable history. Provide experiment list/create/edit/archive and selectors instead of hard-coded `exp_cifar10`.

**F15 — Decisions are not an enforced evidence-backed lifecycle.**
The API accepts empty rationale and arbitrary status, even on unevaluated runs. Optional details are concatenated into one text field; no evidence snapshot or stable alternative references exist. Ordering solely by second-resolution timestamp can make the newest decision ambiguous. Define enums, allowed transitions, required rationale/limitations/alternative analysis, linked evidence, append-only history, deterministic ordering, and a selection policy. Preserve human authorship and historical decisions.

**F16 — Comparison does not support the required analysis.**
A table exists, but no user-selected set of up to four runs, overlaid curves, full parameter matrix, stored test results, measured size, or reproducibility evidence. The overfitting gap combines final training accuracy with best validation accuracy, potentially different epochs; zero-valued metrics are also treated as missing. Compare matched epochs/checkpoints, use null checks, and show metrics with units and evidence links. Compute parameter counts from models: CustomCNN actually has **620,810**, not the displayed ~1.2M.

**F17 — UI run identity and completion state can be wrong.**
`Phase2_Execution.jsx:30` and later phases silently fall back to `runs[0]` when the requested run is missing. The comparison list is not automatically refreshed when execution finishes; downstream evidence may stay stale. Polling starts only when a preloaded run is already RUNNING/QUEUED, creating a launch race. Failed/disconnected states render as running; the stepper marks earlier steps complete simply because the user navigated forward. Use explicit run IDs/routes, authoritative state, reliable invalidation, missing/failed/offline states, and persisted stage eligibility.

**F18 — Image input and serving contracts are incomplete.**
`get_transforms(False)` does not resize; a 64×64 probe stayed `(3,64,64)`, despite the UI promising 32×32. CustomCNN's fixed classifier cannot handle arbitrary sizes. Add explicit preprocessing from the version manifest, bounded image upload/decode validation, stable version metadata in every response, and model cache/loading policy. Blocking model computation inside an async request also needs isolation or controlled dispatch.

**F19 — Validation, transactions, and storage evolution are weak.**
Schemas accept zero epochs, negative batch/LR, unsupported status/config strings, and unknown fields silently. Metrics retrieval ignores the experiment/run relationship. Direct SQL and per-operation commits make workflow invariants difficult to enforce. Add constrained request/response schemas, consistent 4xx errors, scoped lookups, uniqueness/check constraints, migrations and transaction boundaries; safely back up and migrate existing data. Retain SQLite for the local MVP.

### P2 — six delivery and scope repair groups

**F20 — Artifacts and decision reporting are missing.** No artifact listing/download API/UI, CSV logs, report generation, confusion image export, or complete historical decision report. Add artifact manifests and controlled downloads, then generate the decision report from persisted structured evidence. Legacy missing evidence must be marked unknown.

**F21 — UI accessibility and responsive behavior need deliberate work.** Current CSS is light-themed despite dark-mode docs, fixed multi-column layouts have no media queries, several labels lack input associations, and stepper/dropzone are click-only containers. Add responsive layouts, real buttons, keyboard/focus behavior, status announcements, error summaries and verified contrast. For example, muted `#94a3b8` on white and green `#059669` normal-size text warrant correction against 4.5:1. Visual inspection was limited; test 1920×1080 and 1366×768 before claiming compliance. Theme is a product decision, not the main blocker.

**F22 — Error communication and operational visibility are weak.** Fetch helpers discard server details; components use alerts or silently ignore errors. The disconnected UI still says Compute Engine Online and Serving Active. Add actionable errors/retry, true connection state, persistent failed-job reasons, and a bounded event log. Do not fabricate restored timestamps, batch totals, scheduler values, or completed state as `runs.py` currently does.

**F23 — Tests, CI, and reproducible setup are absent.** Establish API contract, lifecycle, migration, worker, trainer and browser tests; CI build/test gates; a pinned/locked backend environment and documented supported versions. Meet the PRD's ≥80% backend coverage using meaningful assertions. Keep costly CIFAR studies as explicit integration/acceptance jobs, with fast synthetic fixtures for routine checks.

**F24 — Documentation overstates implementation.** README checks every development stage complete and advertises workflows that fail. Its example create/launch payloads do not match required schema fields, health response differs, optimizer choice is advertised but trainer fixes AdamW/weight decay, and model metrics are inaccurate. Align docs with executable contracts and measured results; update both duplicated entry documents or declare one canonical source.

**F25 — Scope conflicts and secondary features need an explicit baseline.** Expanded datasets, search/filtering, W&B sync, auth/sessions and parts of reporting are absent. PRD sections disagree on some priorities: full Git/environment lineage is Must in the matrix but Should elsewhere; auth is claimed as covered in the OJT table without a defined matching functional section; early chart timing and strict update latency may conflict with slow CPU epochs and 1.5-second polling. Approve a clarified acceptance baseline. Defer expanded datasets/W&B until the core chain passes. If multi-user use is required, add auth/ownership/session tests before shared access; for local single-user use, document the boundary and restrict CORS appropriately. Missing Tailwind/SQLAlchemy/Docker alone is not equivalent to broken product behavior—agree implementation constraints separately.

## 5. PRD coverage map

“Partial” means some useful implementation exists, not acceptance passed.

| Requirements | Current status | Repair groups |
|---|---|---|
| FR-EXP-01–03 | Partial create/read; no full management, hypothesis, branching | F14, F17, F19 |
| FR-DAT-01–02 | CIFAR-10 implemented; catalog and recorded split/version/transforms missing | F12–14, F25 |
| FR-MDL-01–02 | Four factories; compatibility validation incomplete | F18–19, F25 |
| FR-EXE-01–04 | Real training/background launch; queue/stop/isolation missing | F07–09 |
| FR-TRK-01–03 | Local final persistence; live durable logging/LR and W&B absent | F08, F22, F25 |
| FR-EVL-01–02 | Disconnected holdout helper; secondary metrics missing | F10 |
| FR-REP-01–03 | Partial algorithms; required assurance/reporting absent | F11–13 |
| FR-CMP-01–02 | Summary table only; no chosen four-run overlays | F16 |
| FR-DEC-01–06 | Broken UI submission; insufficient structured history | F01, F05, F14–15 |
| FR-ART-01–03 | Best checkpoint only; artifact lifecycle/downloads absent | F09, F20 |
| FR-REG-01–02 | Unsafe mutable promotion; UI response mismatch | F02, F04, F06 |
| FR-LIN-01 | Partial live join; historical immutable provenance absent | F05, F14–15 |
| FR-PRM-01 | Registration and promotion conflated; serving not bound | F03–04, F18 |
| FR-INF-01–02 | Real forward pass but unreliable source/version/input contract | F03, F18 |
| FR-SRCH-01 | Missing | F14, F25 |
| FR-RPT-01 | Missing | F20 |
| NFR performance/reliability | No benchmarks; persistence/isolation gaps; polling exceeds 500 ms target | F07–08, F22–23, F25 |
| NFR usability/maintainability | Modular starting point; accessibility and coverage unproven | F19, F21, F23 |

## 6. Target architecture

Keep React, FastAPI, SQLite and PyTorch. Improve ownership and contracts rather than adding infrastructure for its own sake.

1. **React views:** investigations; run setup/detail; selected-run comparison; audit detail; decisions/history; registry/version detail; inference. The four-phase guide can remain an onboarding path, but must not replace persistent navigation and saved state.
2. **Typed API contracts:** validated requests, explicit responses/errors, immutable identifiers. Generate or verify the frontend client against OpenAPI to prevent F01/F02 recurring.
3. **Application services:** investigation, execution, evaluation/audit, decision, registry and serving services enforce lifecycle rules and transactions. Routers translate HTTP; they should not own scientific policy.
4. **One local worker process:** durable SQLite jobs plus an atomic claim/admission policy, cancellation flag, heartbeat and recovery rules. Training and both audit modes share scheduling and resource limits. Keep API responsive without concurrent RNG interference.
5. **Training/evaluation engine:** immutable run configuration, independent split/initialization seeds, per-epoch persistence callback, finite-value checks, checkpoint manifests, final evaluation tied to selected weights.
6. **Persistence and artifacts:** versioned migrations; investigation relationships; run config/environment snapshots; metrics; evaluations; audits/member runs; decisions/evidence links; artifacts/checksums; immutable registered versions; explicit active-serving reference.
7. **Inference resolver:** active/promoted version → artifact hash → architecture/preprocessing → verified loaded model. Return model/version/run identifiers with predictions.

Execution state and candidate decision state must be separate. Proposed execution states: QUEUED → RUNNING → EVALUATING → COMPLETED, with STOPPED/FAILED and restart reconciliation. Candidate decisions retain Candidate/Accepted/Rejected/Superseded/Selected. Registration and serving activation are separate lifecycle events.

For legacy records, retain original metrics/checkpoints and annotate missing metadata. Do not manufacture historical Git hashes, environment snapshots, audit results, or predecessor links. Re-run candidates when new verified evidence is necessary.

## 7. Phased change plan for approval

Effort estimates are focused developer-days, not promises; training/benchmark waiting and review may add calendar time. Tests are part of each phase, not postponed to the end. Phases are dependency-ordered and should be reviewed in small changes.

| Phase | Work and findings | Estimate | Exit gate |
|---|---|---:|---|
| **0. Freeze evidence and agree baseline** | Back up SQLite/artifacts, record current dirty-tree baseline, inventory legacy data, resolve F25 priorities and metric units; establish minimal regression harness | 1–2 days | Recoverable backup; approved acceptance matrix; no historic facts invented |
| **1. Stop false success and broken contracts** | F01–06, immediate F18–19 validation and F22 truthfulness fixes; remove fabricated evidence; correct decision/promotion responses; block invalid inference and version overwrite | 3–5 days | UI-shaped contract tests pass; invalid candidate/checkpoint/version/path requests fail safely; no random fallback predictions |
| **2. Durable execution and trustworthy evaluation** | F07–10, F13, run configuration storage, migrations, duplicate-launch protection, stop/restart handling, actual LR and artifact events | 5–8 days | One active job; metrics survive forced failure; cancel/restart states correct; completed candidate has checkpoint-linked holdout evaluation |
| **3. Scientific reproducibility and comparison** | F11–12, F16; shared queue audits; fixed splits; two matching runs; five controlled seeds; persisted statistics and comparison data | 4–6 days | Original config replayed; trajectory mismatch detected; five-seed report survives restart; up to four comparable runs selected |
| **4. Complete investigation and model lifecycle** | F14–15, full lineage/provenance, F04 immutable publication, F18 registered-version serving, F20 core decision reporting | 5–8 days | Reject → linked successor → select → register → activate → predict can be traced back through all evidence and alternatives |
| **5. Complete UI workflows and accessibility** | F17, F21–22; experiment/run navigation, charts, history, registry selector, artifact access, inline errors, responsive and keyboard design | 4–7 days | Browser acceptance flows work after reload; disconnected/failed states truthful; desktop/laptop and keyboard checks pass |
| **6. Verify release and align documentation** | F23–24, remaining core F20 exports, performance measurements, migration rehearsal, clean installation, seeded demonstration dataset/history | 3–5 days | Core PRD use cases pass; ≥80% backend coverage; build/CI green; measured benchmarks and honest README |
| **7. Approved enhancements** | Remaining F25: additional datasets, search depth, W&B, auth if selected scope requires it, optional exports/visualizers | Estimate after baseline approval | Each extension has its own explicit acceptance tests; core scope remains stable |

**Core recovery planning range: 25–41 focused developer-days**, excluding optional Phase 7 and long benchmark waits. Some UI design can proceed alongside backend work, but evidence-dependent screens should use agreed contracts. Re-estimate after Phase 2, when legacy migration and worker behavior are understood. This is a repair program, not a cosmetic polish pass.

## 8. Concrete release acceptance scenarios

1. Create/edit/archive an investigation with objective, hypothesis and targets; reload and reopen it.
2. Launch a valid CIFAR-10 run; reject invalid parameters and duplicate IDs. Attempt a second launch and receive an explicit queued/rejected outcome.
3. Observe persisted epoch metrics while the run is still active, including current LR. Stop the job and retain completed epochs/checkpoints. Simulate failure and restart without phantom running states.
4. Evaluate a known checkpoint on the untouched holdout set; persist exact artifact identity and metrics. Missing artifacts fail visibly.
5. Repeat the same immutable configuration under matching conditions twice; compare trajectories and final test results. Demonstrate a deliberately altered configuration is not reported as a matching-condition pass.
6. Execute five seed runs with a fixed data split and otherwise identical settings; recompute displayed statistics from stored results; reload the report.
7. Compare up to four runs with aligned curves, configuration differences, test metrics, size, duration, latency and uncertainty.
8. Reject an approach with limitations/evidence; create a successor linked to that limitation; preserve both after reload. Select the final candidate with rationale and alternative analysis.
9. Register the selected candidate; reject failed/unselected/unevaluated candidates, missing files and reused versions. Confirm checkpoint hash and stored run agree.
10. Activate that version and predict an uploaded image; return version/run metadata, valid probabilities and latency. Missing/corrupt/unsupported input must never yield a successful random prediction.
11. Starting at the prediction's model ID, navigate back through immutable provenance and the complete investigation reasoning chain. Export a report and download the referenced artifacts.
12. Test disconnected backend, no experiments, empty results, zero accuracy, failing audit, long-running job, keyboard navigation and both PRD viewport sizes. No unknown state may display verified success.

## 9. Review decisions and implementation boundary

Proposed approval scope is Phases 0–6, keeping CIFAR-10 and a local single-user deployment as the core target. Preserve historical data, keep the current technology stack, and prioritize evidence integrity over cosmetic changes. Expanded datasets/cloud sync belong in Phase 7; auth must move into the core if shared-user access is required. Choose light/dark theme and strict versus revised update-latency acceptance during Phase 0.

**No application fixes have been implemented in this audit.** The report, verification output and reusable isolated probe script are the deliverables. Approval should authorize the phased repair work; it should not be interpreted as permission to discard existing work or overwrite historical experiment artifacts.
