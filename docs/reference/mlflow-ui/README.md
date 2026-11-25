# MLflow UI source reference

This folder contains **unchanged, selected frontend source files** from the public MLflow repository. They are for local UI study only and are not imported or compiled by TrainTrace.

- Upstream: https://github.com/mlflow/mlflow
- Source area: `mlflow/server/js/src`
- Branch inspected: `master`
- Commit: `f9fc58bbd532c4b81a063c55ff6d16bc0f0b54bc`
- Commit date: 2026-11-17 10:22:33 UTC
- License: Apache License 2.0; see the copied `LICENSE.txt`.
- These selected files have imports from MLflow's broader frontend and Databricks Design System. This folder is not a standalone/buildable copy of MLflow.

## What to study

- `experiment-tracking/components/ExperimentListView.tsx` and `ExperimentListTable.tsx`: searchable, filterable experiment table and clear row-level metadata.
- `experiment-tracking/components/experiment-page/ExperimentPage.tsx` and `pages/experiment-page-tabs/ExperimentPageTabs.tsx`: experiment header and tab-based organization of related evidence.
- `experiment-tracking/components/run-page/RunPage.tsx`, `RunViewHeader.tsx`, and `RunViewOverview.tsx`: run identity, status, actions, breadcrumbs, and grouped run metadata.
- `experiment-tracking/components/run-page/RunViewMetricCharts.tsx` and `RunViewArtifactTab.tsx`: focused metric and artifact inspection.
- `experiment-tracking/components/CompareRunPage.tsx`, `CompareRunView.tsx`, and `CompareRunMetricTable.tsx`: selecting and comparing run metrics and parameters in aligned views.
- `model-registry/components/ModelListPage.tsx`, `ModelListView.tsx`, `ModelView.tsx`, `ModelVersionView.tsx`, and `RegisterModelForm.tsx`: searchable registry tables, version detail, and registration flow.
- `app.tsx` and `MlflowRouter.tsx`: application shell and route organization.

## TrainTrace adaptation notes

Use MLflow's information hierarchy and interaction patterns, not its branding or large-platform feature set. TrainTrace's matching areas are Investigations, Training/run details, Compare, Decisions/History, Registry, and Inference. Audits and the viva notebook are TrainTrace-specific and should stay first-class. Keep TrainTrace's own requirements: durable queued training, investigation reasoning, reproducibility protocols, per-epoch metrics, and evidence-bound model decisions.
