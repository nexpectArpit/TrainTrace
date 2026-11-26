import React, { useState } from "react";
import { Badge, fmt } from "./Common";
import styles from "./RunList.module.css";

const datasetName = (run) =>
  run.config?.dataset_name ||
  run.dataset?.dataset_name ||
  run.dataset?.name ||
  "Unknown";

export default function RunList({ runs, selectedId, onOpen, onCompare }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState(null);
  const columns = [
    ["Approach", (run) => run.approach_name],
    ["Status", (run) => run.status],
    ["Dataset", datasetName],
    ["Architecture", (run) => run.model_architecture],
    ["Epochs", (run) => run.metrics?.length],
    ["Best validation", (run) => run.best_val_accuracy],
    [
      "Recorded time",
      (run) => (run.metrics?.length ? run.total_duration_sec : null),
    ],
    ["Actions", null],
  ];
  const visible = runs
    .filter((run) => {
      const text =
        `${run.approach_name || ""} ${run.id} ${run.model_architecture || ""} ${datasetName(run)}`.toLowerCase();
      return (
        text.includes(search.trim().toLowerCase()) &&
        (!status || run.status === status)
      );
    })
    .sort((a, b) => {
      if (!sort) return 0;
      const first = columns[sort.index][1](a);
      const second = columns[sort.index][1](b);
      if (first == null && second == null) return 0;
      if (first == null) return 1;
      if (second == null) return -1;
      const compared =
        typeof first === "number" && typeof second === "number"
          ? first - second
          : String(first).localeCompare(String(second), undefined, {
              numeric: true,
              sensitivity: "base",
            });
      return sort.direction === "ascending" ? compared : -compared;
    });
  return (
    <section className={styles.section} aria-labelledby="runs-list-heading">
      <header className={styles.heading}>
        <div>
          <h2 id="runs-list-heading">Investigation runs</h2>
          <p>
            {runs.length} recorded {runs.length === 1 ? "run" : "runs"}. Open
            one to inspect its saved and live evidence.
          </p>
        </div>
        <span>{visible.length} shown</span>
      </header>
      <div className={styles.filters}>
        <label>
          Find a run
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Approach, model, dataset or ID"
          />
        </label>
        <label>
          Execution status
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All statuses</option>
            {["QUEUED", "RUNNING", "COMPLETED", "FAILED", "STOPPED"].map(
              (value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ),
            )}
          </select>
        </label>
      </div>
      {visible.length ? (
        <div
          className={styles.scroll}
          role="region"
          aria-label="Investigation run list"
          tabIndex={0}
        >
          <table className={styles.table}>
            <caption>Runs in the selected investigation</caption>
            <thead>
              <tr>
                {columns.map(([label, accessor], index) => (
                  <th
                    scope="col"
                    key={label}
                    aria-sort={
                      sort?.index === index ? sort.direction : undefined
                    }
                  >
                    {accessor ? (
                      <button
                        type="button"
                        className={styles.sort}
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
              {visible.map((run) => (
                <tr
                  key={run.id}
                  className={run.id === selectedId ? styles.selected : ""}
                >
                  <th scope="row">
                    <button
                      type="button"
                      className={`link ${styles.open}`}
                      title={`${run.approach_name || "Unnamed approach"} · ${run.id}`}
                      onClick={() => onOpen(run)}
                    >
                      {run.approach_name || "Unnamed approach"}
                    </button>
                  </th>
                  <td>
                    <Badge value={run.status} />
                  </td>
                  <td>{datasetName(run)}</td>
                  <td>{run.model_architecture || "Unknown"}</td>
                  <td>
                    {run.metrics?.length ?? 0} / {run.epochs ?? "?"}
                  </td>
                  <td>
                    {run.best_val_accuracy == null
                      ? "—"
                      : `${fmt(run.best_val_accuracy)}%`}
                  </td>
                  <td>
                    {run.metrics?.length
                      ? `${fmt(run.total_duration_sec, 1)} s`
                      : "—"}
                  </td>
                  <td>
                    <button type="button" onClick={() => onOpen(run)}>
                      Open
                    </button>
                    {run.status === "COMPLETED" && (
                      <button type="button" onClick={() => onCompare(run)}>
                        Compare
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className={styles.empty}>
          {runs.length
            ? "No runs match these filters. Clear the search or status to see them."
            : "No runs yet. Configure the first approach below."}
        </p>
      )}
    </section>
  );
}
