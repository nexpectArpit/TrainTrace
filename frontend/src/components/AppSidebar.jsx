import React from "react";
import { Badge } from "./Common";
import { navGroups, tabLabels, tabIconPaths } from "../app/config";
import SidebarNavItem from "./design-system/SidebarNavItem";

export default function AppSidebar({ workspace, collapsed, setCollapsed }) {
  const { tab, setTab, online, info, jobs } = workspace;

  return (
    <aside className="app-sidebar">
      <a href="#main" className="skip">
        Skip to content
      </a>
      <div className="sidebar-brand-row">
        <a
          href="/"
          className="brand"
          aria-label="TrainTrace home"
          onClick={(event) => {
            event.preventDefault();
            setTab("Investigations");
            window.history.replaceState(
              null,
              "",
              window.location.pathname + window.location.search,
            );
            document.getElementById("main")?.focus();
          }}
        >
          <img
            className="brand-logo brand-logo-dark"
            src="/brand/traintrace-logo-dark.png"
            alt="TrainTrace"
          />
          <img
            className="brand-mark-image brand-mark-dark"
            src="/brand/traintrace-mark-dark.png"
            alt=""
            aria-hidden="true"
          />
          <small className="brand-caption">
            Evidence-led ML investigations
          </small>
        </a>
        <button
          type="button"
          className="sidebar-collapse-button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => setCollapsed(!collapsed)}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" fill="none">
            <path
              fill="currentColor"
              fillRule="evenodd"
              clipRule="evenodd"
              d="M1.75 1a.75.75 0 0 0-.75.75v12.5c0 .414.336.75.75.75H15v-1.5H5.5v-11H15V1zM4 2.5H2.5v11H4z"
            />
            <path
              fill="currentColor"
              d={
                collapsed
                  ? "M11.19 8.75 9.97 9.97l1.06 1.06L14.06 8l-3.03-3.03-1.06 1.06 1.22 1.22H7v1.5z"
                  : "m9.81 8.75 1.22 1.22-1.06 1.06L6.94 8l3.03-3.03 1.06 1.06-1.22 1.22H14v1.5z"
              }
            />
          </svg>
        </button>
      </div>
      <nav className="workspace-nav" aria-label="Workspace">
        {navGroups.map((group) => (
          <div className="nav-group" key={group.label}>
            <span className="nav-group-label">{group.label}</span>
            {group.items.map((item) => (
              <SidebarNavItem
                key={item}
                label={tabLabels[item] || item}
                active={tab === item}
                iconPath={tabIconPaths[item]}
                onClick={() => setTab(item)}
              />
            ))}
          </div>
        ))}
      </nav>
      <div
        className="sidebar-status"
        title={`${online ? "API online" : "API offline"} · Worker ${online ? (info?.worker_online ? "online" : "offline") : "unknown"}`}
      >
        <Badge value={online ? "API ONLINE" : "API OFFLINE"} />
        <p>
          {online
            ? info?.hardware?.name
            : "Connect the backend to load verified state."}
        </p>
        <small>
          Worker:{" "}
          {online ? (info?.worker_online ? "online" : "offline") : "unknown"} ·{" "}
          {online ? (info?.queued_jobs ?? "—") : "—"} queued
        </small>
      </div>
    </aside>
  );
}
