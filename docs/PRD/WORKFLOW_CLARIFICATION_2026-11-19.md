# TrainTrace workflow clarification — 2026-11-19

This addendum clarifies the user journey in PRD v5.2. It does not change the stored experiment, run, decision, checkpoint, or model contracts.

1. The primary research loop is **Investigations → Runs → Compare → Decisions**. Users may repeat Runs and Compare for any number of approaches within an investigation.
2. **Candidate image testing** is available for completed, intact checkpoints in Compare. An uploaded image produces prediction, confidence, and latency. Correctness is shown only when the user supplies a known label. A single image never supplies a dataset accuracy estimate.
3. **Reproducibility** is optional supporting evidence. Same-seed replays and controlled seed variation are available from the comparison context; neither is required to record a candidate decision.
4. **Final holdout evaluation** remains sealed during candidate comparison. After a researcher selects one candidate, one final test evaluation may be reserved for that investigation. The reservation freezes candidate decisions and cannot be treated as another comparison run.
5. **Model registration** is optional for research and candidate image testing. It requires the selected decision, completed final evaluation, intact provenance, and the evaluated checkpoint. Registration creates an immutable named version. Activation chooses which registered version serves predictions.
6. **Investigation history** is a contextual timeline and report, reachable from the investigation workspace. Search is a header utility, not a research stage.

## Implementation status

The initial navigation and checkpoint/serving placement is implemented. Full screen redesign, styling consolidation, chart refinement, and end-to-end browser verification remain open under `docs/audits/2026-11-19/PRODUCT_WORKFLOW_AND_UI_REDESIGN_PLAN.md`.
