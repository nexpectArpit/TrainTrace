# First UI page review: Investigations

Scope: `frontend/src/screens/Investigations.jsx` and its direct data behavior. This checklist records the initial analysis and the UI iteration that followed it.

## Field-by-field review

| Field / control | Why it exists | What the code currently does | Recommendation for the next code iteration |
|---|---|---|---|
| Search investigations by name or ID | Finds a saved record to resume. | Filters the loaded list by name and ID only. | Keep. Later consider archive/status filters if the list becomes large; not necessary to add another field now. |
| Investigation name | Human-readable identity in lists and reports. | Required, stored, shown in cards and reports. | Keep; add a clear validation message if duplicate names are allowed (IDs, not names, are the unique identity). |
| Objective | States the problem being investigated. | Required, stored, shown in the investigation list and report. | Keep; this is core to the PRD's decision traceability. |
| Hypothesis | Records the prediction being tested. | Required and stored; shown in reports. | Keep; this is also core to the PRD. Encourage a testable statement in helper text. |
| Target test accuracy (%) | Intended quantitative success target. | Optional and stored as `target_accuracy`. There is no code that compares this target with a run result or marks it met. The word “test” is hazardous: repeatedly tuning against holdout/test accuracy leaks evaluation information. | **Remove this input from the current create form in the next code iteration.** It currently says “test” and is not compared with results. If target tracking is implemented later, reintroduce it as “Target validation accuracy (%)” with visible target-versus-result reporting; reserve holdout/test data for final evaluation. No removal yet in this analysis step. |
| Target latency per sample (ms) | Intended deployment/runtime constraint. | Optional and stored as `target_latency_ms`; no target-versus-measured check exists. The measured latency is only meaningful with consistent hardware/batching/timing methodology, so a number without that context can mislead. | **Remove this input from the current form in the next code iteration.** Reintroduce it only after measurement conditions are defined and the report can show whether the target was met. No removal yet in this analysis step. |
| Conclusion | Captures the investigation outcome and rationale. | Optional on edit, shown as “Not recorded” until filled, included in reports. | Keep, but make clear it is an end-of-investigation summary; it does not need to be part of creation. |
| Archive investigation | Closes an investigation without deleting history. | Available only while editing. Archived investigations cannot launch new runs; they remain stored and listed with an Archived badge. | Keep. Consider a list filter later; do not remove the archive control. |
| Open investigation / Currently open | Selects the context for other tabs. | Switches the active investigation. | Keep; necessary navigation, not an experiment parameter. |
| Configure an approach | Takes the user to run configuration. | Switches to Training tab. | Keep; this is the next step in the workflow. |
| Download full decision report / CSV | Lets users inspect and export evidence. | Downloads the markdown report and comparison/epoch CSV. | Keep; aligns with reporting requirements. |
| Candidate/completed run counts | Quick progress summary. | Shows candidate run count and completed count. | Keep, but “candidate” currently appears to mean all associated runs; verify/rename if this count does not reflect an actual candidate status. |

## Missing or weakly surfaced on this page

- **Investigation parent/branch link:** PRD requirement FR-EXP-03 calls for parent-child investigation linking and visible branching history. The API schema has a `parent_run_id` property, but this creation form does not expose it and this page does not show an investigation ancestry/branch view. Add a parent investigation/run selector and lineage display in a later iteration if FR-EXP-03 remains in scope.
- **Metric target status:** Target fields are currently passive metadata. Either implement a comparison in the record/report or remove/defer the inputs; storing a target alone does not help users judge success.
- **Edit labels:** Existing edit controls show internal keys (`target_accuracy`, `target_latency_ms`) instead of user-facing labels. Replace with the final product labels if these fields remain.

## Next-iteration checklist

- [x] Remove the current target accuracy and target latency inputs from the investigation create/edit UI.
- [ ] If target accuracy is restored later, call it validation accuracy and show target-vs-result; never encourage tuning against holdout/test accuracy.
- [ ] If target latency is restored later, define and display measurement conditions and target-vs-result.
- [ ] Implement or explicitly de-scope PRD FR-EXP-03 investigation parent/child linking and visualization.
- [ ] Keep the required name, objective, and hypothesis fields; keep archive, search, reports, and workflow navigation.
- [ ] Give the editable target fields accessible user-facing labels if retained.

## Training / pretrained status from the current local database and code

- Current code trains models through its PyTorch training worker. `CustomCNN` is randomly initialized. ResNet-18, MobileNetV2, and EfficientNet-B0 can optionally initialize from torchvision ImageNet weights; the UI default is unchecked and the API default is `pretrained=False`.
- The local database has 16 historical run records. Of those, one record has `pretrained=true`, and its status is `FAILED`; no completed record in the current database records `pretrained=true`. Several completed modern-format records have `pretrained=false`, including CustomCNN and ResNet-18. Older records do not contain a `pretrained` setting, so their initialization method cannot be established from the stored run config alone.
- Therefore: **the project has trained models; its completed, explicitly configured runs in this database used scratch initialization. Pretrained transfer learning is supported but this database does not show a completed pretrained run.** This statement is limited to the current local database and does not establish what may have been run elsewhere or before the stored configs were captured.
