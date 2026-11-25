# TrainTrace MVP refactor

Status: implementation in progress. This file distinguishes completed changes from work that still needs validation.

## Shared shell and landing

- Implemented shared theme preference, landing illustration module, favicon, landing scroll behavior, and lazy dashboard loading on entry.
- Remaining: inspect desktop and mobile layouts in a browser; consolidate landing styles and shared design tokens.

## Run lifecycle and Kaggle execution

- Split cloud credentials, kernel generation/submission, telemetry parsing, artifact ingestion, and polling into `backend/cloud/` modules.
- Removed the call to `kernels_stop`: the installed Kaggle SDK does not provide it. TrainTrace now states that a local stop can leave the remote Kaggle kernel running.
- Persist malformed telemetry as an operational event instead of discarding it silently. A focused persistence check covers stage, batch, epoch, and malformed markers.
- Removed the fabricated Kaggle username. Cloud status now distinguishes configured credentials from successful authentication, the launch form waits for verification, and the backend verifies the account again before queuing a cloud run.
- A missing Kaggle status now displays a connection state and has a configurable grace period before TrainTrace stops monitoring with a clear error. Remote execution may still continue in that case.
- Remaining: verify a real Kaggle launch through artifact download and inference; bound individual SDK calls; exercise remote deletion, connection loss, and restart recovery; validate migrations against an older storage snapshot. Remote cancellation requires a supported Kaggle API or explicit user action on Kaggle.

## Training workspace

- `Training.jsx` owns run selection and form synchronization. Execution evidence lives in `RunExecutionPanel`; chart preferences and CSV export live in `useLiveChartSettings`, while chart controls and rendering live in separate components. Form validation and field metadata live in `runFormSchema`. The form delegates core controls to `RunSetupFields`, schedule and lineage to `AdvancedRunSettings`, and cloud credential entry to `ExecutionTargetSelector`.
- Live polling lives in `useLiveRun`. Charts use persisted samples and clear stale readings when the response has no samples.
- Tag search now has its own hook with stale-response protection; run filtering is a pure selector outside `useWorkspace`. Remaining: simplify the rest of the workspace state interface and inspect chart bounds and progress states in the browser.

## Comparison and inference

- `Compare.jsx` delegates filters and the sortable candidate table to feature components.
- `Inference.jsx` delegates checkpoint selection, image upload, serving prediction, and checkpoint comparison results to feature components. `useCheckpointComparison` owns candidate loading, selection, preview, and request state.
- Backend inference now separates upload decoding and checkpoint execution from checkpoint lookup and recorded dataset validation. Missing class names, dataset identity, or preprocessing settings produce a clear conflict instead of CIFAR-10 defaults.
- Remaining: browser-check checkpoint selection and upload flows; verify how old artifacts lacking the recorded upload adapter should be migrated or reported to users.

## Scientific pipeline and storage

- Split environment and checkpoint hashing, optional W&B integration, CSV metric export, dataset preparation monitoring, batch sample persistence, and final evaluation measurements from the local training coordinator. Partial-epoch samples are flushed when a run stops or fails.
- All local datasets now enter through one loader path; CIFAR-10 no longer takes a separate runtime branch.
- Local training and generated Kaggle code now use the same five-dataset catalog and preprocessing contract source. Both reject datasets that do not provide the expected class names instead of inventing numeric labels.
- Notebook export now embeds the shared dataset/preprocessing source and uses a separate, readable dataset cell with the same split and augmentation recipe. It rejects incomplete or warm-start configurations instead of quietly changing the experiment. The final-test cell remains opt-in.
- Remaining: keep explicit historical readers only where needed to open existing artifacts; remove silent substitutions. Verify final test remains isolated from candidate selection in a full run.

## Acceptance before calling the refactor complete

- Exercise local and cloud launch → stage/batch updates → completion → artifact inspection → inference.
- Exercise stop, remote deletion, connection loss, and restart recovery.
- Inspect dark and light themes, navigation, focus states, chart bounds, and mobile layout in a browser.
- Report cloud execution as unverified until a real remote run succeeds.
