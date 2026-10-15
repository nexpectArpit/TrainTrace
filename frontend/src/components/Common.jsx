import React from "react";
export const activeStates = ["QUEUED", "RUNNING", "EVALUATING"];
export const architectures = [
  "custom_cnn",
  "resnet18",
  "mobilenet_v2",
  "efficientnet_b0",
];
export const freshRun = () => ({
  run_id: `run_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`,
  approach_name: "",
  model_name: "custom_cnn",
  epochs: 2,
  batch_size: 128,
  learning_rate: 0.001,
  seed: 42,
  split_seed: 42,
  pretrained: false,
  scheduler_type: "constant",
  optimizer: "adamw",
  weight_decay: 0.0001,
  predecessor_run_id: null,
  motivating_reason: "",
});
export const emptyExperiment = {
  name: "",
  objective: "",
  hypothesis: "",
  conclusion: "",
  target_accuracy: null,
  target_latency_ms: null,
  archived: false,
};
export const emptyDecision = {
  status: "CANDIDATE",
  rationale: "",
  limitations: "",
  alternatives_considered: "",
  why_not_alternative: "",
  tradeoff_acknowledged: "",
  next_investigation: "",
};
export const fmt = (v, d = 2) =>
  v === null || v === undefined ? "—" : Number(v).toFixed(d);
export function Badge({ value }) {
  return (
    <span
      className={`badge ${["COMPLETED", "SELECTED", "ACTIVE"].includes(value) ? "good" : ["FAILED", "STOPPED", "REJECTED"].includes(value) ? "bad" : ""}`}
    >
      {value || "Unknown"}
    </span>
  );
}
export function Field({
  name,
  label,
  value,
  onChange,
  type = "text",
  required = false,
  ...rest
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {type === "textarea" ? (
        <textarea
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          {...rest}
        />
      ) : (
        <input
          name={name}
          type={type}
          value={value ?? ""}
          onChange={(e) =>
            onChange(
              type === "number"
                ? e.target.value === ""
                  ? null
                  : Number(e.target.value)
                : e.target.value,
            )
          }
          required={required}
          {...rest}
        />
      )}
    </label>
  );
}
export function Select({ label, value, onChange, children, ...rest }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select
        aria-label={label}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        {...rest}
      >
        {children}
      </select>
    </label>
  );
}
export function Panel({ title, children, action }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Json({ data, label = "View stored evidence" }) {
  return (
    <details>
      <summary>{label}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

export const formatTime = (value) =>
  value ? new Date(value.replace(" ", "T") + "Z").toLocaleString() : "Unknown";
