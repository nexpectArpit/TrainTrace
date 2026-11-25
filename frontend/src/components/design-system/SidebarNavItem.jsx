import React from "react";

/** TrainTrace navigation adapter based on MLflow's MlflowSidebarLink styling. */
export default function SidebarNavItem({ label, active, iconPath, onClick }) {
  return (
    <button
      type="button"
      className="workspace-nav-item"
      aria-label={label}
      title={label}
      aria-current={active ? "page" : undefined}
      onClick={onClick}
    >
      <svg
        className="nav-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path d={iconPath} />
      </svg>
      <span>{label}</span>
    </button>
  );
}
