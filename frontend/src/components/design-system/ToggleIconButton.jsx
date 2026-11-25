import React from "react";

/**
 * TrainTrace adapter for MLflow's common/components/ToggleIconButton.tsx.
 * Keeps its pressed-state, icon-only interaction, and quiet hover treatment
 * without pulling in MLflow's analytics and Databricks theme providers.
 */
export default function ToggleIconButton({
  pressed,
  onClick,
  label,
  title = label,
  className = "",
  children,
}) {
  return (
    <button
      type="button"
      className={`mlflow-icon-button ${className}`.trim()}
      aria-label={label}
      aria-pressed={pressed}
      title={title}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
