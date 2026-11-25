# Second UI page review: Training

Scope: the Training tab, its shared context selectors in `frontend/src/App.jsx`, and the corresponding launch/training behavior. This checklist began as a review; checked items below were implemented in the Training UI iteration.

## Run setup fields

| Field / control | Why it exists and what code does | Recommendation |
|---|---|---|
| Investigation selector (shared context bar) | Associates a run with an active investigation. Changing it resets selected run and setup state. | Keep. Clearly show the selected investigation at the top of the run form; archived records cannot queue runs. |
| Candidate run selector (shared context bar) | Chooses which run's progress, charts, metrics, events, and artifacts to inspect. It lists approach name and status. | Keep, but include a short run ID in each option so similarly named runs can be distinguished. “Run to inspect” is clearer than “Candidate run” here. |
| Shared search field | Searches investigation choices and is used to filter `visibleRuns` in other views. The Training form and run selector read the unfiltered `runs` list, so typing a run name does not filter this page's selector. | Keep only if its effect is made clear on Training; otherwise scope its label/help per page or wire it to the Training run selector. |
| Run ID (unique) | Stable machine identity for artifacts, API, checkpoints, and lineage. `freshRun()` already generates a unique ID. | Do not remove the ID from the underlying run. Hide it under advanced details or make it read-only with a copy/regenerate action; it does not need to be a required editable field for ordinary users. |
| Approach name | Human-readable label for this specific configuration/run. | Keep; it makes run lists and reports understandable. Add a short example. |
| Dataset | Chooses CIFAR-10 or CIFAR-100 and drives class count, normalization, labels, evaluation, and inference metadata. | Keep; core choice. The text says split counts are fixed, which is accurate for current code. Make the fixed split proportions explicit or show them in a compact “Data protocol” summary. |
| Architecture | Chooses CustomCNN, ResNet-18, MobileNetV2, or EfficientNet-B0. | Keep. Replace raw identifiers (`custom_cnn`, `mobilenet_v2`, etc.) with display names and one-line descriptions. Clarification #2 permits fixed internals for preset families. |
| Optimizer | Selects AdamW or SGD; SGD uses momentum 0.9 in code. | Keep. Show the fixed SGD momentum in the option/helper text. Expose momentum only if optimizer tuning is intended. |
| Learning-rate schedule | Selects constant, cosine, or step scheduling. Code uses cosine over all epochs; StepLR currently has fixed `step_size=2` and `gamma=0.5`. | Keep the schedule choice, but either expose the StepLR parameters or label it as a fixed preset and record the effective values in run provenance. |
| CustomCNN convolution blocks | Sets depth from 2–6; this is a real architecture control saved in run config/checkpoint and used to reconstruct the model. | Keep. This is block-level depth control, not arbitrary per-layer topology editing; label it accurately. |
| CustomCNN starting channels | Sets the width of the first block; later blocks widen according to implementation. | Keep; explain the scaling behavior and that parameter count/compute will grow. |
| CustomCNN classifier units | Sets hidden classifier width. | Keep; make clear it controls the classifier head. |
| CustomCNN dropout | Sets dropout probability. | Keep; current range is 0–0.95 in steps of 0.05. Explain it as regularization, not a layer count. |
| Epochs | Number of complete train/validation passes; hard limit 1–1000. | Keep. Consider a sensible suggested range and a training-time warning; 1000 is valid but can be very expensive. |
| Batch size | Samples per optimizer step; affects memory and optimization behavior. | Keep. Add a concise memory/throughput hint and an actionable OOM explanation if launch fails. |
| Learning rate | Optimizer step scale. | Keep. Add a brief hint that it is optimizer-sensitive; avoid claiming there is one universally correct value. |
| “Initialization seed” | Code seeds Python, NumPy, PyTorch, device RNGs, and the training data-loader shuffle. It is not only a weight-initialization seed; with pretrained weights, only newly initialized parameters begin from random initialization. | Keep the control, rename it to “Run randomness seed” (or “Training seed”), and explain the RNG scope. |
| Dataset split seed | Controls the deterministic train/validation partition. The test/holdout set comes from the dataset's separate test partition. | Keep and label its distinct role; same split seed is needed for direct comparisons on the same partition. |
| Weight decay | Passed to AdamW/SGD as regularization. | Keep; it is a meaningful training hyperparameter. Add a short description and note zero disables it. |
| ImageNet initialization checkbox | For ResNet-18/MobileNetV2/EfficientNet-B0, optionally loads torchvision ImageNet weights before training on the selected CIFAR dataset. Defaults off. CustomCNN cannot use this. | Keep for preset models. When CustomCNN is selected, replace the disabled checkbox with explanatory text (“CustomCNN trains from scratch”) or hide it; a disabled-looking control without explanation is confusing. |
| Predecessor run | Associates this run with an earlier run after it has a recorded decision. | Keep for lineage. Show run ID and the predecessor's recorded limitation/decision, not only its approach name. |
| Why investigate this approach? | Records the reason for branching; required by backend when a predecessor run is selected. | Keep and make it required when a predecessor is selected, with helper text asking which limitation this run addresses. |
| Queue training run | Submits the validated config to the durable sequential worker queue. It is disabled if backend is offline, no active investigation, investigation archived, or worker offline. | Keep. Explain the disabled reason beside the button; current disabled state alone does not tell the user what to fix. |

## Execution and results panel

| Display / control | Why it exists | Recommendation |
|---|---|---|
| Stop run | Cancels a queued/running/evaluating job; completed epoch evidence is retained. | Keep. Show a clear confirmation/state message after a successful stop. |
| Execution status and epochs persisted | Shows job lifecycle and durable completed-epoch count. | Keep; this is useful live status. |
| Best validation accuracy and elapsed epoch time | Quick view of run progress/performance. | Keep; label time as elapsed training/evaluation duration if that is what the backend value represents. |
| Live batch progress | Shows epoch, batch, current LR, and running batch accuracy. | Keep, but label batch accuracy as provisional so it is not confused with epoch validation accuracy. |
| Validation accuracy/loss charts | Shows per-epoch learning behavior. | Keep; useful to detect under/over-fitting. |
| Persisted epoch table | Makes training and validation metrics inspectable. | Keep; consider collapsing on small screens or allowing CSV export nearby. |
| Execution events | Shows recent run messages. | Keep; “latest 300” is implementation detail and can move into disclosure/help text. |
| Configuration/provenance JSON | Exposes full stored configuration, dataset and environment information. | Keep as a disclosure for power users; provide a human-readable summary before the raw JSON. |
| Artifacts | Links to checkpoint and metrics artifacts with size and SHA256. | Keep; make artifact names more descriptive and distinguish best/last checkpoints. |

## Implemented in this UI iteration

- The Run ID stays generated automatically; custom editing is tucked under advanced details.
- Architecture choices now use readable labels. The run selector includes IDs and responds to the shared search.
- Seed labels/help clarify run randomness versus data split randomness.
- The page explains fixed SGD momentum and StepLR values, fixed preset architecture layouts, and scratch initialization for CustomCNN.
- Predecessor choices show IDs and decision state; selecting one reveals its recorded limitation.
- Queue prerequisites now show a reason when launch is unavailable.
- Batch-memory and epoch-time guidance is visible, and fixed split counts are stated.
- Existing CustomCNN controls, run metrics, checkpoints, charts, stop action, provenance, and artifact links remain available.

## Highest-priority next-iteration work

- [x] Keep Run ID generated by default and move the custom-ID override into advanced details.
- [x] Rename “Initialization seed” to “Run randomness seed” and explain its scope.
- [x] Replace architecture enum strings with human-readable names/descriptions.
- [x] Explain fixed SGD momentum and StepLR values in the UI; dynamic controls remain a later improvement.
- [x] Scope the shared search label on Training and wire it to run selection.
- [x] Show predecessor IDs, decision status, and the recorded limitation.
- [x] Explain backend, worker, investigation, and archive blockers beside the queue button.
- [x] Replace the disabled ImageNet checkbox for CustomCNN with a clear scratch-training explanation.
- [x] Preserve the four CustomCNN controls: block depth, starting width, classifier width, and dropout.
- [x] Preserve dataset, optimizer, scheduler, epochs, batch size, learning rate, seeds, weight decay, stop control, durable metrics, charts, provenance, and artifact access.

## Evidence and scope notes

- Current domain contract: `backend/domain.py` `LaunchRun` and `CustomCNNConfig`.
- Actual training behavior: `backend/tracking/tracker.py`, `backend/core/dataset.py`, `backend/core/trainer.py`, and `backend/core/models.py`.
- The 2026-11-17 PRD clarification says CIFAR-10/100 are the current dataset scope, and requires CustomCNN depth, width, classifier width, and dropout controls. It allows preset architecture families to retain fixed internal layouts.
- The current Training UI shows the fixed 45,000/5,000/10,000 split; it does not offer arbitrary split ratios or augmentation selection. Existing run metadata records split counts, split seed, preprocessing, augmentation, and dataset hashes.
