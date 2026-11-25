import React from "react";
import { Field, Select, TagsField } from "../../components/Common";
import { trainingFields, isNumberInRange } from "./runFormSchema";

export default function AdvancedRunSettings({
  setup,
  setSetup,
  runs,
  advancedInvalid,
}) {
  const predecessorRun = runs.find((r) => r.id === setup.predecessor_run_id);
  return (
    <details className="training-advanced-settings">
      <summary>
        Advanced settings{" "}
        <span>
          {advancedInvalid
            ? "Review invalid advanced values"
            : "schedule, data split, regularization, lineage and checkpoint"}
        </span>
      </summary>
      <div className="grid three">
        <Select
          label="Learning-rate schedule"
          info={
            setup.scheduler_type === "step"
              ? "Step decay halves the learning rate every two epochs; this preset is fixed."
              : setup.scheduler_type === "cosine"
                ? "Cosine decay gradually reduces the learning rate across the selected training epochs."
                : "Constant keeps the configured learning rate unchanged during training."
          }
          value={setup.scheduler_type}
          onChange={(v) => setSetup({ ...setup, scheduler_type: v })}
          required
        >
          <option value="constant">Constant learning rate</option>
          <option value="cosine">Cosine decay</option>
          <option value="step">Step decay</option>
        </Select>
        {trainingFields
          .filter(([key]) => ["split_seed", "weight_decay"].includes(key))
          .map(([k, l, min, max, step, info, rangeLabel]) => (
            <Field
              key={k}
              label={l}
              info={info}
              type="number"
              step={step}
              min={min}
              max={max}
              rangeLabel={rangeLabel}
              aria-invalid={!isNumberInRange(setup[k], min, max, step)}
              required
              value={setup[k]}
              onChange={(v) => setSetup({ ...setup, [k]: v })}
            />
          ))}
      </div>
      <TagsField
        value={setup.tags}
        onChange={(tags) => setSetup({ ...setup, tags })}
        info="Optional key=value labels for filtering and grouping runs, such as owner=arpit or dataset=pilot."
      />
      <Select
        label="Continue investigation from a prior run"
        info="Optionally link this run to a prior decision whose recorded limitation motivates the new approach. This preserves the investigation history."
        value={setup.predecessor_run_id || ""}
        onChange={(v) => setSetup({ ...setup, predecessor_run_id: v || null })}
      >
        <option value="">Initial approach</option>
        {runs
          .filter((r) => r.latest_decision)
          .map((r) => (
            <option key={r.id} value={r.id}>
              {r.approach_name} · {r.id} · {r.latest_decision.status}
            </option>
          ))}
      </Select>
      {predecessorRun && (
        <div className="predecessor-context">
          <strong>Recorded predecessor limitation</strong>
          <p>
            {predecessorRun.latest_decision.limitations ||
              "No limitation was recorded for this decision."}
          </p>
        </div>
      )}
      <Select
        label="Initialize from a saved run checkpoint (optional)"
        info="Continue from a prior run's model weights. The optimizer and learning-rate schedule restart fresh; the checkpoint architecture and class count must match."
        value={setup.initialize_from_run_id || ""}
        onChange={(v) =>
          setSetup({ ...setup, initialize_from_run_id: v || null })
        }
      >
        <option value="">Start with the selected initialization above</option>
        {runs
          .filter(
            (r) =>
              ["COMPLETED", "STOPPED", "FAILED"].includes(r.status) &&
              (r.artifacts || []).some((a) =>
                ["best_checkpoint", "last_checkpoint"].includes(a.kind),
              ),
          )
          .map((r) => (
            <option key={r.id} value={r.id}>
              {r.approach_name} · {r.id} · {r.model_architecture}
            </option>
          ))}
      </Select>
      <Field
        label="Why investigate this approach?"
        info="Record the question or limitation this run addresses. Required when linking to a predecessor run so the lineage has a clear rationale."
        type="textarea"
        value={setup.motivating_reason}
        required={!!setup.predecessor_run_id}
        placeholder="What limitation or question does this run address?"
        onChange={(v) => setSetup({ ...setup, motivating_reason: v })}
      />
    </details>
  );
}
