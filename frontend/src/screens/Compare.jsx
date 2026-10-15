import React from "react";
import MetricChart from "../components/MetricChart";
import {
  architectures,
  fmt,
  Badge,
  Field,
  Select,
  Panel,
  Json,
} from "../components/Common";
export default function Compare({ workspace }) {
  const {
    setTab,
    setRunId,
    runs,
    compare,
    setCompare,
    archFilter,
    setArchFilter,
    statusFilter,
    setStatusFilter,
    seedFilter,
    setSeedFilter,
    accuracyMin,
    setAccuracyMin,
    visibleRuns,
    chosen,
    metrics,
  } = workspace;
  return (
    <Panel title="Compare candidate evidence">
      <p>
        Select up to four runs. All accuracy values use percent; overfitting
        gaps compare training and validation from the same final epoch.
      </p>
      <div className="grid four">
        <Select
          label="Architecture filter"
          value={archFilter}
          onChange={setArchFilter}
        >
          <option value="">All</option>
          {architectures.map((a) => (
            <option key={a}>{a}</option>
          ))}
        </Select>
        <Select
          label="Status filter"
          value={statusFilter}
          onChange={setStatusFilter}
        >
          <option value="">All</option>
          {[
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "STOPPED",
            "SELECTED",
            "REJECTED",
            "SUPERSEDED",
            "ACCEPTED",
          ].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </Select>
        <Field
          label="Seed filter"
          type="number"
          value={seedFilter}
          onChange={(v) => setSeedFilter(v === null ? "" : String(v))}
        />
        <Field
          label="Minimum test accuracy (%)"
          type="number"
          min="0"
          max="100"
          value={accuracyMin}
          onChange={(v) => setAccuracyMin(v === null ? "" : String(v))}
        />
      </div>
      <div className="table-wrap">
        <table>
          <caption>Candidate runs</caption>
          <thead>
            <tr>
              {[
                "Compare",
                "Approach",
                "Execution",
                "Decision",
                "Val acc %",
                "Test acc %",
                "Gap pp",
                "Params",
                "Checkpoint MB",
                "Duration s",
                "Latency ms",
              ].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRuns.map((r) => (
              <tr key={r.id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Compare ${r.approach_name}`}
                    checked={compare.includes(r.id)}
                    disabled={!compare.includes(r.id) && compare.length >= 4}
                    onChange={(e) =>
                      setCompare(
                        e.target.checked
                          ? [...compare, r.id]
                          : compare.filter((id) => id !== r.id),
                      )
                    }
                  />
                </td>
                <td>
                  <button
                    className="link"
                    onClick={() => {
                      setRunId(r.id);
                      setTab("Training");
                    }}
                  >
                    {r.approach_name}
                  </button>
                  <small>
                    {r.model_architecture} · seed {r.seed}
                  </small>
                </td>
                <td>
                  <Badge value={r.status} />
                </td>
                <td>
                  <Badge value={r.latest_decision?.status || "CANDIDATE"} />
                </td>
                <td>{fmt(r.best_val_accuracy)}</td>
                <td>{fmt(r.evaluation?.test_accuracy)}</td>
                <td>{fmt(r.overfitting_gap)}</td>
                <td>
                  {r.evaluation?.parameter_count?.toLocaleString() || "Unknown"}
                </td>
                <td>
                  {r.evaluation
                    ? fmt(r.evaluation.model_size_bytes / 1e6)
                    : "—"}
                </td>
                <td>{fmt(r.total_duration_sec, 1)}</td>
                <td>{fmt(r.evaluation?.latency_ms_per_sample, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!visibleRuns.length && <div className="empty">No matching runs.</div>}
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
      {chosen.map((r) => (
        <Json
          key={r.id}
          data={{
            configuration: r.config,
            evaluation: r.evaluation,
            audits: r.audits,
          }}
          label={`${r.approach_name}: configuration, holdout metrics and reproducibility`}
        />
      ))}
    </Panel>
  );
}
