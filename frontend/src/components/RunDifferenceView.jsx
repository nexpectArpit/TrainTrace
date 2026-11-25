import React, { useEffect, useState } from "react";
import styles from "./RunDifferenceView.module.css";

const fields = [
  ["dataset_name", "Dataset", (config) => config.dataset_name],
  ["model_name", "Architecture", (config) => config.model_name],
  ["pretrained", "Pretrained weights", (config) => config.pretrained],
  ["depth", "CNN depth", (config) => config.architecture_config?.depth],
  ["width", "CNN width", (config) => config.architecture_config?.width],
  [
    "classifier_width",
    "Classifier width",
    (config) => config.architecture_config?.classifier_width,
  ],
  ["dropout", "Dropout", (config) => config.architecture_config?.dropout],
  ["epochs", "Planned epochs", (config) => config.epochs],
  ["batch_size", "Batch size", (config) => config.batch_size],
  ["optimizer", "Optimizer", (config) => config.optimizer],
  ["learning_rate", "Learning rate", (config) => config.learning_rate],
  ["scheduler_type", "Schedule", (config) => config.scheduler_type],
  ["weight_decay", "Weight decay", (config) => config.weight_decay],
  ["seed", "Training seed", (config) => config.seed],
  ["split_seed", "Data split seed", (config) => config.split_seed],
];

function displayValue(value) {
  if (value === undefined || value === null || value === "") return "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function RunDifferenceView({ runs }) {
  const [baselineId, setBaselineId] = useState(runs[0]?.id || "");
  const [differencesOnly, setDifferencesOnly] = useState(true);
  useEffect(() => {
    if (!runs.some((run) => run.id === baselineId))
      setBaselineId(runs[0]?.id || "");
  }, [runs, baselineId]);
  if (runs.length < 2) return null;

  const baseline = runs.find((run) => run.id === baselineId) || runs[0];
  const visibleFields = fields.filter(([, , read]) => {
    if (!differencesOnly) return true;
    const original = displayValue(read(baseline.config || {}));
    return runs.some(
      (run) => displayValue(read(run.config || {})) !== original,
    );
  });

  return (
    <section className={styles.section} aria-labelledby="run-differences-title">
      <div className={styles.heading}>
        <div>
          <h3 id="run-differences-title">Configuration differences</h3>
          <p>
            Compare recorded training settings. The baseline is a visual
            reference; changing it does not change any run.
          </p>
        </div>
        <div className={styles.controls}>
          <label>
            Baseline
            <select
              value={baseline.id}
              onChange={(event) => setBaselineId(event.target.value)}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.approach_name}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={differencesOnly}
              onChange={(event) => setDifferencesOnly(event.target.checked)}
            />
            Show only differences
          </label>
        </div>
      </div>
      {visibleFields.length ? (
        <div
          className={styles.scroller}
          role="region"
          aria-label="Run configuration comparison"
          tabIndex={0}
        >
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Setting</th>
                {runs.map((run) => (
                  <th scope="col" key={run.id}>
                    {run.approach_name}
                    {run.id === baseline.id && <small>Baseline</small>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleFields.map(([key, label, read]) => {
                const original = displayValue(read(baseline.config || {}));
                return (
                  <tr key={key}>
                    <th scope="row">{label}</th>
                    {runs.map((run) => {
                      const value = displayValue(read(run.config || {}));
                      const changed = value !== original;
                      return (
                        <td
                          key={run.id}
                          className={changed ? styles.changed : undefined}
                        >
                          {value}
                          {changed && (
                            <span className={styles.changeLabel}>Changed</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className={styles.empty}>
          These runs have the same recorded settings. Training results can still
          differ because of execution or data conditions.
        </p>
      )}
    </section>
  );
}
