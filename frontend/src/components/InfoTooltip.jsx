import React, { useId } from "react";
import styles from "./InfoTooltip.module.css";

/** Compact, keyboard and touch accessible explanation for a field or section. */
export default function InfoTooltip({ label = "More information", children }) {
  const tooltipId = useId();
  return (
    <span className={styles.root}>
      <button
        className={styles.trigger}
        type="button"
        aria-label={label}
        aria-controls={tooltipId}
        aria-describedby={tooltipId}
      >
        i
      </button>
      <span className={styles.tooltip} id={tooltipId} role="tooltip">
        {children}
      </span>
    </span>
  );
}
