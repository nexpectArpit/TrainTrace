# MLflow UI and TrainTrace frontend skeleton review

**Review date:** 2026-11-18  
**MLflow source:** full local checkout at `../mlflow-upstream-retry`, commit `b6c922375ddd3f5816a1324eaec81d343413b2b1` (2026-11-17).  
**Scope:** source inspection only; no application changes and no tests run.

## Summary

MLflow is a broad experiment tracking and model lifecycle platform. TrainTrace has a much smaller React shell, but it is aimed at a narrower and distinct workflow: launch a controlled PyTorch experiment, preserve the reason for it, compare results, run reproducibility protocols, record a human decision, then register and serve the selected model. The PRD explicitly prioritizes decision traceability and reproducible deep learning. Therefore the useful comparison is in navigation, information hierarchy, run browsing, metadata extensibility and detail views; MLflow's feature count is not a direct measure of TrainTrace completeness.

The complete MLflow source checkout is present locally. Its UI is in `mlflow-upstream-retry/mlflow/server/js/src`. The selected-file reference under `traintrace/docs/reference/mlflow-ui` remains a curated, older snapshot at commit `f9fc58b`; use the full checkout as authoritative for current behavior.

## Frontend skeleton comparison

| Area | MLflow | TrainTrace | Assessment |
|---|---|---|---|
| Frontend size and structure | Large TypeScript/React application split by product domain, with shared components, state/data layers and routes. It uses React Router, Redux, React Query/Apollo in parts, and Databricks Design System. | 13 application source files under `frontend/src`; React/Vite with 8 screen components and a single 618-line `App.jsx` plus 1,792-line `App.css`. | TrainTrace is a compact prototype-scale frontend. Its app shell currently owns screen selection, global state, API refresh and screen coordination. |
| Navigation | URL routes and nested page layouts; experiment and run details have subroutes/tabs and can be linked directly. | Tabs controlled in `App.jsx`, saved to local storage. No URL route per screen or selected entity. | Deep links, browser history and reloadable page state are a clear structural gap. |
| UI system | Shared design-system components and consistent patterns across product areas. | A small `Common.jsx` set of `Field`, `Select`, `Panel`, `Badge`, etc., with most styling in one large stylesheet. | Continue extracting shared patterns where repeated; do not import MLflow's Databricks-specific component stack wholesale. |
| Data flow | Domain components use established API/state/query abstractions. | One top-level `refresh()` fetches experiments, system information, registry models, jobs and the selected experiment's comparison matrix, then passes a shared `workspace` object to screens. | Simple and understandable at current scale, but increasingly coupled as features grow. Screen-specific data and actions are centralized in one shell. |

## What MLflow's UI actually offers

- Experiment browser: create, search/filter, compare and delete experiments; list metadata such as name, creation/modification time, description/tags; paginate and handle loading/empty/error states.
- Experiment workspace: a route-based header and a configurable set of feature tabs, including runs, traces, models, datasets, evaluations, prompts and other flag- or experiment-type-dependent features.
- Run browser and details: searchable/compareable runs and a run detail page organized into overview, model metrics, system metrics, traces/evaluations and artifacts. Run identity, status, metadata and actions are separated from detailed evidence.
- Model registry: model and version views, registration from a logged run, lineage and version metadata/actions.
- Specialized creation flows exist for prompt/evaluation work. These are separate from the normal ML run creation path.

The standard MLflow run creation action accepts an experiment ID, tags and optional run name (`mlflow/server/js/src/experiment-tracking/actions.ts`, `createRunApi`). It does not expose epochs, optimizer, dataset, layer count or other generic deep-learning launch controls. The `useCreateNewRun` wrapper opens `EvaluationCreatePromptRunModal` only when the Prompt Lab feature is enabled. In the typical MLflow workflow, the training script or notebook starts training and logs parameters, metrics and artifacts to MLflow. Thus MLflow is not evidence that TrainTrace needs fewer training controls; its standard UI has a different job.

## TrainTrace fields and feature coverage

TrainTrace already exposes meaningful model-run controls in `frontend/src/screens/Training.jsx`:

- Dataset: CIFAR-10 or CIFAR-100; architecture: Custom CNN, ResNet-18, MobileNetV2 or EfficientNet-B0; optional ImageNet initialization for preset architectures.
- Custom CNN depth (2–6 blocks), starting channels (8–128), classifier width (16–2048) and dropout (0–0.95).
- Optimizer AdamW or SGD; learning-rate schedule constant, cosine or step. SGD momentum and step-scheduler gamma/step size are fixed presets, explicitly disclosed in the UI.
- Epochs, batch size, learning rate, initialization seed, dataset split seed and weight decay.
- Approach name, optional predecessor run and motivating reason; generated run ID is in a collapsed advanced section.
- The same screen also presents live execution, metrics, events and configuration/provenance, combining launch and run inspection.

This is already substantial user control over the supported training pipeline. Important scope distinction: depth/width controls only apply to Custom CNN; preset architectures retain fixed internal layouts. The UI says so. Training is not an arbitrary neural-network builder.

TrainTrace's distinctive PRD workflow is not represented by standard MLflow: investigations with hypotheses/reports, exact-replay and multi-seed audits, human evidence-backed decisions, successor rationale/history, immutable releases and version-bound inference. Preserve these as first-class pages. MLflow's generic run metadata, searching, filtering, routeable details and separation of overview/metrics/artifacts are the most relevant patterns to borrow.

## Gaps to address in future iterations

1. **Frontend architecture and navigation:** split the monolithic app shell into route/layout, data hooks and page components; make investigation and run details addressable by URL; retain selection across refresh/deep link.
2. **Run discovery:** make run browsing a first-class table/view with consistent search, sort, useful columns and empty/loading/error behavior. Current comparison filters are useful, but filtering is not a substitute for a general run list.
3. **Run detail organization:** separate run summary/configuration, training metrics, audit/evaluation evidence, artifacts and provenance into clear sections or tabs. Training currently mixes configuration and execution detail.
4. **Metadata extensibility:** keep required reproducibility fields typed, while considering optional tags/notes for user-defined context. Do not add generic fields without a use case or persistence contract.
5. **Provenance completeness:** verify that dataset version/split, transform policy, code revision, dependency versions and hardware/runtime are captured and visible for every run. The UI refers to historical provenance but this review did not validate every backend provenance field.
6. **Shared UI consistency:** use MLflow as a reference for hierarchy, tables, state treatment and detail navigation. Avoid importing its design-system dependencies or duplicating its enterprise feature surface.

## Specific UI defect noticed

`frontend/src/screens/Registry.jsx` currently gives the Semantic version `Field` two `placeholder` props in the same JSX element: `v1.0.0` and `e.g. cifar100-best`. JavaScript/JSX keeps the latter value, so the displayed placeholder does not match the version field's intended format. This is a concrete UI cleanup item for the next code iteration.

## Evidence inspected

- PRD: `docs/PRD/Tracked_Training_Pipeline_PRD.md`, especially product positioning, goals and first-class decision traceability.
- TrainTrace frontend: `frontend/src/App.jsx`, `frontend/src/screens/Training.jsx`, `Compare.jsx`, `Registry.jsx`, and `frontend/package.json`.
- MLflow shell/router: `mlflow-upstream-retry/mlflow/server/js/src/MlflowRouter.tsx` and experiment tracking route/component sources.
- MLflow run creation: `mlflow-upstream-retry/mlflow/server/js/src/experiment-tracking/actions.ts` and `components/experiment-page/hooks/useCreateNewRun.tsx`.
- MLflow details and experiment form: `components/run-page/RunViewModeSwitch.tsx` and `components/modals/CreateExperimentForm.tsx`.

**Conclusion:** TrainTrace has its core domain workflow and meaningful training controls, but its frontend skeleton is substantially less modular and less navigable than MLflow. The next improvement should focus on a routeable shell, run discovery/detail organization, and provenance visibility while preserving TrainTrace's decision and reproducibility workflow.
