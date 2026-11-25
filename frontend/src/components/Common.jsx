import React, { useEffect, useState } from "react";
import InfoTooltip from "./InfoTooltip";
import badgeStyles from "./StatusBadge.module.css";

function FieldLabel({ label, required, info }) {
  return (
    <span>
      {label}
      {required && (
        <span className="required-indicator" aria-hidden="true">
          *
        </span>
      )}
      {info && <InfoTooltip label={`About ${label}`}>{info}</InfoTooltip>}
    </span>
  );
}

export function RequiredFieldLegend() {
  return (
    <p className="required-fields-legend">
      <span aria-hidden="true">*</span> Required fields
    </p>
  );
}
export const activeStates = ["QUEUED", "RUNNING", "EVALUATING"];
export const architectures = [
  "custom_cnn",
  "resnet18",
  "mobilenet_v2",
  "efficientnet_b0",
];
export const datasets = [
  "cifar10",
  "cifar100",
  "mnist",
  "fashion_mnist",
  "svhn",
];
export const DEFAULT_ARCHITECTURE_CONFIG = {
  depth: 3,
  width: 32,
  classifier_width: 256,
  dropout: 0.3,
};
export const freshRun = () => ({
  run_id: `run_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`,
  approach_name: "",
  dataset_name: "cifar10",
  model_name: "custom_cnn",
  architecture_config: { ...DEFAULT_ARCHITECTURE_CONFIG },
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
  initialize_from_run_id: null,
  tags: {},
  motivating_reason: "",
  execution_target: "local",
});
export const emptyExperiment = {
  name: "",
  objective: "",
  hypothesis: "",
  conclusion: "",
  target_accuracy: null,
  target_latency_ms: null,
  archived: false,
  tags: {},
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
export const evidenceText = (value) =>
  typeof value === "string" && value.trim() && /^\.+$/.test(value.trim())
    ? "Not recorded (legacy record)."
    : value || "Not recorded (legacy record).";
export const canShowFinalEvaluation = (run) =>
  run?.latest_decision?.status === "SELECTED" &&
  run?.final_evaluation_status === "COMPLETED" &&
  !!run?.final_evaluation &&
  !run.final_evaluation.legacy_preselection_test_exposure;

export function TagsField({
  value = {},
  onChange,
  label = "Tags (optional)",
  info,
}) {
  const serialize = (tags) =>
    Object.entries(tags || {})
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
  const [draft, setDraft] = useState(() => serialize(value));
  const [tagError, setTagError] = useState("");
  useEffect(() => setDraft(serialize(value)), [value]);
  return (
    <label className="field">
      <FieldLabel label={label} info={info} />
      <input
        value={draft}
        placeholder="e.g. dataset=pilot, owner=research"
        aria-invalid={!!tagError}
        onChange={(event) => {
          setDraft(event.target.value);
          setTagError("");
          event.target.setCustomValidity("");
        }}
        onBlur={(event) => {
          const next = {};
          const parts = draft
            .split(",")
            .map((part) => part.trim())
            .filter(Boolean);
          const invalid =
            parts.length > 50 ||
            parts.some((part) => {
              const split = part.indexOf("=");
              if (split < 1) return true;
              const key = part.slice(0, split).trim();
              const val = part.slice(split + 1).trim();
              if (
                !/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/.test(key) ||
                val.length > 256 ||
                key in next
              )
                return true;
              next[key] = val;
              return false;
            });
          const message = invalid
            ? "Use at most 50 unique key=value tags, separated by commas. Keys start with a letter; values can be at most 256 characters."
            : "";
          setTagError(message);
          event.target.setCustomValidity(message);
          if (!invalid) onChange(next);
        }}
      />
      {tagError && (
        <small className="field-error" role="alert">
          {tagError}
        </small>
      )}
    </label>
  );
}
export function Badge({ value }) {
  const normalized = String(value || "").toUpperCase();
  const tone = [
    "COMPLETED",
    "SELECTED",
    "ACTIVE",
    "API ONLINE",
    "VERIFIED",
    "CORRECT",
    "✓ CORRECT",
    "ACCEPTED",
  ].includes(normalized)
    ? "success"
    : ["QUEUED", "PENDING"].includes(normalized)
      ? "warning"
      : [
            "FAILED",
            "REJECTED",
            "API OFFLINE",
            "INCORRECT",
            "✕ INCORRECT",
          ].includes(normalized)
        ? "danger"
        : normalized === "RUNNING"
          ? "info"
          : "neutral";
  return (
    <span className={`badge ${badgeStyles.base} ${badgeStyles[tone]}`}>
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
  info,
  rangeLabel,
  ...rest
}) {
  const min = rest.min;
  const max = rest.max;
  const step = rest.step;
  const numericValue = Number(value);
  const numericStep = step && step !== "any" ? Number(step) : null;
  const stepBase = min != null ? Number(min) : 0;
  const stepMismatch =
    numericStep != null &&
    Number.isFinite(numericValue) &&
    Math.abs(
      (numericValue - stepBase) / numericStep -
        Math.round((numericValue - stepBase) / numericStep),
    ) > 1e-7;
  const rangeInvalid =
    type === "number" &&
    value !== null &&
    value !== undefined &&
    value !== "" &&
    (!Number.isFinite(numericValue) ||
      (min != null && numericValue < Number(min)) ||
      (max != null && numericValue > Number(max)) ||
      stepMismatch);
  const range =
    rangeLabel ||
    (min != null && max != null
      ? `Allowed: ${min}–${max}`
      : min != null
        ? `Minimum: ${min}`
        : max != null
          ? `Maximum: ${max}`
          : "");
  const stepHint =
    step && step !== "1" && step !== "any" ? ` · increments of ${step}` : "";
  return (
    <label className="field">
      <FieldLabel label={label} required={required} info={info} />
      {type === "textarea" ? (
        <textarea
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          {...rest}
          aria-invalid={rest["aria-invalid"] || rangeInvalid || undefined}
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
          aria-invalid={rest["aria-invalid"] || rangeInvalid || undefined}
        />
      )}
      {type === "number" && range && (
        <small className="field-range-hint">
          {range}
          {stepHint}
        </small>
      )}
    </label>
  );
}
export function Select({
  label,
  value,
  onChange,
  children,
  info,
  required = false,
  ...rest
}) {
  return (
    <label className="field">
      <FieldLabel label={label} required={required} info={info} />
      <select
        aria-label={label}
        value={value ?? ""}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        {...rest}
      >
        {children}
      </select>
    </label>
  );
}
export function Panel({ title, children, action, headingId }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2 id={headingId}>{title}</h2>
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
