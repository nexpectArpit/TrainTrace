import React from "react";
import { Badge, fmt, canShowFinalEvaluation } from "../../components/Common";

export default function CandidateRunsTable({
  sortedRuns,
  visibleRuns,
  sortColumns,
  sort,
  setSort,
  compare,
  setCompare,
  setRunId,
  setTab,
  displayDataset,
}) {
  return (
    <>
      <p className="table-scroll-hint">
        Scroll horizontally to see every run metric →
      </p>
      <div
        className="table-wrap table-scroll"
        role="region"
        aria-label="Candidate runs table; scroll horizontally for more columns"
        tabIndex={0}
      >
        <table className="compare-runs-table">
          <caption>Candidate runs</caption>
          <thead>
            <tr>
              {sortColumns.map(([label, accessor], index) => (
                <th
                  key={label}
                  scope="col"
                  aria-sort={sort?.index === index ? sort.direction : undefined}
                >
                  {accessor ? (
                    <button
                      type="button"
                      className="compare-sort-button"
                      onClick={() =>
                        setSort({
                          index,
                          direction:
                            sort?.index === index &&
                            sort.direction === "ascending"
                              ? "descending"
                              : "ascending",
                        })
                      }
                    >
                      {label}
                      {sort?.index === index
                        ? sort.direction === "ascending"
                          ? " ↑"
                          : " ↓"
                        : ""}
                    </button>
                  ) : (
                    label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map((r) => (
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
                  {displayDataset(r)}
                  {r.dataset?.num_classes != null && (
                    <small>{r.dataset.num_classes} classes</small>
                  )}
                </td>
                <td>
                  <Badge value={r.status} />
                </td>
                <td>
                  <Badge value={r.latest_decision?.status || "CANDIDATE"} />
                </td>
                <td>{fmt(r.best_val_accuracy)}</td>
                <td>
                  {canShowFinalEvaluation(r)
                    ? `${fmt(r.final_evaluation.test_accuracy)}%`
                    : r.final_evaluation?.legacy_preselection_test_exposure
                      ? "Legacy result withheld"
                      : r.latest_decision?.status === "SELECTED"
                        ? "Evaluation pending"
                        : "Sealed until selected"}
                </td>
                <td>{fmt(r.overfitting_gap)}</td>
                <td>
                  {r.evaluation?.parameter_count?.toLocaleString() || "Unknown"}
                </td>
                <td>
                  {r.evaluation
                    ? fmt(r.evaluation.model_size_bytes / 1e6)
                    : "—"}
                </td>
                <td>
                  {r.metrics?.length
                    ? fmt(r.total_duration_sec, 1)
                    : "Not measured"}
                </td>
                <td>
                  {canShowFinalEvaluation(r)
                    ? fmt(r.final_evaluation.model_only_latency_ms_p50, 3)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!visibleRuns.length && <div className="empty">No matching runs.</div>}
    </>
  );
}
