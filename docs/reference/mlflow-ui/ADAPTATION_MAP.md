# MLflow UI source inspection and TrainTrace adaptation

Inspected at upstream commit `f9fc58bbd532c4b81a063c55ff6d16bc0f0b54bc`. Only the source files listed in the adjacent README were copied. These comparisons describe UI structure and interaction patterns, not feature parity.

| TrainTrace page | Relevant MLflow UI | Pattern to adapt | TrainTrace-specific behavior to preserve |
|---|---|---|---|
| Investigations | Experiment list and experiment page | Grouped left navigation, searchable records, clear identity/description, explicit detail navigation | Objective/hypothesis, archive lifecycle, report exports, investigation context |
| Training | Run page and run overview | Strong run identity/status header, grouped metadata, readable metrics and artifacts | Durable queue, configurable CustomCNN, live progress, cancellation, epoch persistence |
| Compare | Run comparison page | Filter toolbar, selected-run comparison, aligned metric/parameter views | Holdout-versus-validation distinctions, overfit gap, dataset/seed filters, max four runs |
| Audits | No direct equivalent for the local reproducibility protocol | Separate action area from evidence/results; status and result summary per protocol | Protocol A exact replay and Protocol B multi-seed study |
| Decisions | No direct equivalent for human decision capture | Focused form with decision status and grouped evidence context | Frozen evidence, alternatives, limitations, trade-offs, successor rationale |
| History | Experiment/run lineage views | Clear parent-child path and run status/evidence cards | Motivating limitation, candidate decisions, branch action |
| Registry | Model list, model detail, version views, registration form | Searchable table/list, version-centric detail, clear active state | Immutable manifest/checksum, activation, lineage verification |
| Inference | No direct equivalent in the inspected classic tracking flow | Model/version identity before action and a clear result panel | Version-bound preprocessing, per-class probabilities, provenance and errors |
| Viva notebook | No equivalent web page | Keep as an external analysis surface linked to run evidence | Jupyter inspection of metrics, evaluation, and checkpoint tensors |

MLflow's source uses a large shared design system and is not a drop-in component library for this React app. TrainTrace adopts the information hierarchy, navigation, tables, status treatments, and grouped details while keeping its own name, scope, data contracts, and workflow.
