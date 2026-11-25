import React from "react";
import { fmt, Select } from "../../components/Common";
import { MAX_COMPARE_RUNS } from "./useCheckpointComparison";

export default function CheckpointPicker({ comparison, architectureLabels }) {
  const {
    candidates,
    candidatesLoading,
    expFilter,
    setExpFilter,
    selectedRunIds,
    setSelectedRunIds,
    setCompareError,
    setCompareResult,
    investigationOptions,
    visibleCandidates,
    selectedCandidates,
    selectedDatasetKeys,
    toggleRun,
  } = comparison;
  const ARCH_LABELS = architectureLabels;
  return (
    <>
      {investigationOptions.length > 1 && (
        <Select
          label="Filter completed runs by investigation"
          value={expFilter}
          onChange={(value) => {
            setExpFilter(value);
            setCompareError("");
          }}
        >
          <option value="">
            All investigations ({candidates.length} completed runs)
          </option>
          {investigationOptions.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </Select>
      )}

      <fieldset className="checkpoint-picker">
        <legend>
          Completed runs to compare
          <span className="required-indicator" aria-hidden="true">
            *
          </span>
        </legend>
        <div className="checkpoint-picker-toolbar">
          <span role="status">
            {selectedRunIds.length} selected (1–{MAX_COMPARE_RUNS} runs)
          </span>
          <div className="checkpoint-picker-actions">
            <button
              type="button"
              className="link"
              disabled={!visibleCandidates.length}
              onClick={() => {
                setCompareResult(null);
                setCompareError("");
                setSelectedRunIds(
                  visibleCandidates
                    .slice(0, MAX_COMPARE_RUNS)
                    .map((item) => item.run_id),
                );
              }}
            >
              Select visible (up to {MAX_COMPARE_RUNS})
            </button>
            <button
              type="button"
              className="link"
              disabled={!selectedRunIds.length}
              onClick={() => {
                setCompareResult(null);
                setCompareError("");
                setSelectedRunIds([]);
              }}
            >
              Clear selection
            </button>
          </div>
        </div>

        {candidatesLoading && !candidates.length ? (
          <p className="empty">Loading verified completed runs…</p>
        ) : !visibleCandidates.length ? (
          <p className="empty">
            No completed runs with saved best checkpoints are available yet.
            Complete a training run first.
          </p>
        ) : (
          <div className="checkpoint-option-list">
            {visibleCandidates.map((item) => {
              const checked = selectedRunIds.includes(item.run_id);
              const disabled =
                !checked && selectedRunIds.length >= MAX_COMPARE_RUNS;
              const checkboxId = `compare-run-${item.run_id}`;
              return (
                <div
                  key={item.run_id}
                  className={`checkpoint-option${checked ? " is-selected" : ""}`}
                >
                  <input
                    id={checkboxId}
                    type="checkbox"
                    name="run_ids"
                    value={item.run_id}
                    checked={checked}
                    disabled={disabled}
                    onChange={(e) => toggleRun(item.run_id, e.target.checked)}
                  />
                  <label htmlFor={checkboxId}>
                    <strong>{item.approach_name}</strong>
                    <small>
                      {ARCH_LABELS[item.model_architecture] ||
                        item.model_architecture}{" "}
                      · {item.dataset_name} · val{" "}
                      {fmt(item.validation_accuracy)}% · epoch{" "}
                      {item.checkpoint_epoch ?? "—"} · {item.run_id}
                    </small>
                  </label>
                </div>
              );
            })}
          </div>
        )}
      </fieldset>

      {selectedDatasetKeys.length > 1 && (
        <p className="field-range-hint" role="status">
          Selected runs were trained on different datasets (
          {selectedCandidates
            .map((c) => c.dataset_name)
            .filter((v, i, arr) => arr.indexOf(v) === i)
            .join(", ")}
          ). Ground-truth matching will apply only to runs whose class list
          includes your entered label.
        </p>
      )}
    </>
  );
}
