import CompareFilters from "../features/comparison/CompareFilters";
import CandidateRunsTable from "../features/comparison/CandidateRunsTable";
import React, { useState } from "react";
import MetricChart from "../components/MetricChart";
import RunDifferenceView from "../components/RunDifferenceView";
import Inference from "./Inference";
import { fmt, Panel, Json, canShowFinalEvaluation } from "../components/Common";
export default function Compare({ workspace }) {
  const [sort, setSort] = useState(null);
  const {
    setTab,
    setRunId,
    runs,
    compare,
    setCompare,
    visibleRuns,
    chosen,
    metrics,
  } = workspace;
  const comparisonKeys = chosen.map((candidate) => {
    const dataset =
      candidate.config?.dataset_name ||
      candidate.dataset?.dataset_name ||
      candidate.dataset?.name;
    const split = candidate.config?.split_seed;
    return dataset && split !== null && split !== undefined
      ? `${String(dataset).toLowerCase()}:${split}`
      : null;
  });
  const comparableSelection =
    chosen.length < 2 ||
    (comparisonKeys.every(Boolean) && new Set(comparisonKeys).size === 1);
  const displayDataset = (candidate) => {
    const name =
      candidate.config?.dataset_name ||
      candidate.dataset?.dataset_name ||
      candidate.dataset?.name;
    if (!name) return "Unknown";
    return (
      {
        cifar10: "CIFAR-10",
        cifar100: "CIFAR-100",
        fashion_mnist: "Fashion-MNIST",
        mnist: "MNIST",
        svhn: "SVHN",
      }[String(name).toLowerCase()] || String(name).replaceAll("_", "-")
    );
  };
  const sortColumns = [
    ["Compare", null],
    ["Approach", (r) => r.approach_name],
    ["Dataset", displayDataset],
    ["Execution", (r) => r.status],
    ["Decision", (r) => r.latest_decision?.status || "CANDIDATE"],
    ["Val acc %", (r) => r.best_val_accuracy],
    [
      "Test acc %",
      (r) =>
        canShowFinalEvaluation(r) ? r.final_evaluation.test_accuracy : null,
    ],
    ["Gap pp", (r) => r.overfitting_gap],
    ["Params", (r) => r.evaluation?.parameter_count],
    ["Checkpoint MB", (r) => r.evaluation?.model_size_bytes],
    ["Duration s", (r) => (r.metrics?.length ? r.total_duration_sec : null)],
    [
      "Model p50 ms",
      (r) =>
        canShowFinalEvaluation(r)
          ? r.final_evaluation.model_only_latency_ms_p50
          : null,
    ],
  ];
  const sortedRuns = sort
    ? [...visibleRuns].sort((a, b) => {
        const valueA = sortColumns[sort.index][1](a);
        const valueB = sortColumns[sort.index][1](b);
        if (valueA == null && valueB == null) return 0;
        if (valueA == null) return 1;
        if (valueB == null) return -1;
        const comparison =
          typeof valueA === "number" && typeof valueB === "number"
            ? valueA - valueB
            : String(valueA).localeCompare(String(valueB), undefined, {
                numeric: true,
                sensitivity: "base",
              });
        return sort.direction === "ascending" ? comparison : -comparison;
      })
    : visibleRuns;
  return (
    <>
      <Panel
        title="Compare candidate evidence"
        action={
          <button
            type="button"
            onClick={() =>
              document
                .getElementById("candidate-checkpoints")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          >
            Try an image on checkpoints ↓
          </button>
        }
      >
        <p>
          Select up to four runs. All accuracy values use percent; overfitting
          gaps compare training and validation from the same final epoch.
        </p>
        <CompareFilters workspace={workspace} />
        {!!chosen.length && (
          <div
            className="compare-selected-runs"
            aria-label="Selected comparison runs"
          >
            {chosen.map((candidate) => (
              <button
                type="button"
                key={candidate.id}
                title={`Remove ${candidate.approach_name} from comparison`}
                onClick={() =>
                  setCompare(compare.filter((id) => id !== candidate.id))
                }
              >
                <span className="compare-selected-name">
                  {candidate.approach_name}
                </span>
                <span aria-hidden="true">×</span>
              </button>
            ))}
          </div>
        )}
        <CandidateRunsTable
          sortedRuns={sortedRuns}
          visibleRuns={visibleRuns}
          sortColumns={sortColumns}
          sort={sort}
          setSort={setSort}
          compare={compare}
          setCompare={setCompare}
          setRunId={setRunId}
          setTab={setTab}
          displayDataset={displayDataset}
        />
        {chosen.length ? (
          <>
            {!comparableSelection && (
              <p className="notice" role="status">
                These runs use different datasets or recorded data split seeds,
                or their split is unknown. Their validation scores are not a
                like-for-like comparison, so trajectories are shown separately.
              </p>
            )}
            {comparableSelection ? (
              <div className="grid two">
                <MetricChart
                  runs={chosen}
                  field="val_acc"
                  title="Validation accuracy (%) by epoch"
                />
                <MetricChart
                  runs={chosen}
                  field="val_loss"
                  title="Validation loss by epoch"
                />
              </div>
            ) : (
              chosen.map((candidate) => (
                <div className="grid two" key={candidate.id}>
                  <MetricChart
                    runs={[candidate]}
                    field="val_acc"
                    title={`${candidate.approach_name} · validation accuracy (%)`}
                  />
                  <MetricChart
                    runs={[candidate]}
                    field="val_loss"
                    title={`${candidate.approach_name} · validation loss`}
                  />
                </div>
              ))
            )}
          </>
        ) : (
          <div className="empty">
            Select one or more runs in the table to compare their epoch metrics.
          </div>
        )}
        <RunDifferenceView runs={chosen} />
        {chosen.map((r) => (
          <React.Fragment key={r.id}>
            <Json
              data={{
                configuration: r.config,
                validation: r.validation,
                final_test_evaluation: canShowFinalEvaluation(r)
                  ? r.final_evaluation
                  : null,
                audits: r.audits,
              }}
              label={`${r.approach_name}: configuration, validation evidence, final test metrics and reproducibility`}
            />
            <details>
              <summary>
                {r.approach_name}: accessible epoch metric table
              </summary>
              <div className="table-wrap">
                <table>
                  <caption>
                    {r.approach_name} · epoch metrics (accuracy in percent)
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Epoch</th>
                      <th scope="col">Train loss</th>
                      <th scope="col">Train accuracy %</th>
                      <th scope="col">Validation loss</th>
                      <th scope="col">Validation accuracy %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.metrics.map((metric) => (
                      <tr key={metric.id || `${r.id}_${metric.epoch}`}>
                        <th scope="row">{metric.epoch}</th>
                        <td>{fmt(metric.train_loss, 4)}</td>
                        <td>{fmt(metric.train_acc, 2)}</td>
                        <td>{fmt(metric.val_loss, 4)}</td>
                        <td>{fmt(metric.val_acc, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </React.Fragment>
        ))}
      </Panel>
      <section
        id="candidate-checkpoints"
        aria-label="Try an image on completed checkpoints"
      >
        <Inference
          workspace={workspace}
          mode="candidates"
          preferredRunIds={compare}
        />
      </section>
    </>
  );
}
