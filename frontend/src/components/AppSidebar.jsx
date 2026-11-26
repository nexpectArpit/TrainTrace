import React from "react";
import { Badge } from "./Common";
import { navGroups, tabLabels, tabIconPaths } from "../app/config";
import SidebarNavItem from "./design-system/SidebarNavItem";

export default function AppSidebar({
  workspace,
  collapsed,
  setCollapsed,
  sidebarWidth = 244,
  setSidebarWidth,
  setSidebarResizing,
  minWidth = 190,
  maxWidth = 360,
  defaultWidth = 244,
}) {
  const { tab, setTab, online, info } = workspace;

  const startResize = (event) => {
    if (event.button !== 0 || !setSidebarWidth) return;
    event.preventDefault();
    setSidebarResizing?.(true);
    const prevCursor = document.body.style.cursor;
    const prevSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (moveEvent) => {
      const nextX = moveEvent.clientX;
      if (nextX < 125) {
        setCollapsed(true);
      } else {
        setCollapsed(false);
        const clamped = Math.min(
          maxWidth,
          Math.max(minWidth, Math.round(nextX)),
        );
        setSidebarWidth(clamped);
      }
    };

    const onUp = () => {
      setSidebarResizing?.(false);
      document.body.style.cursor = prevCursor;
      document.body.style.userSelect = prevSelect;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

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
            window.history.pushState(null, "", "/");
            window.dispatchEvent(new PopStateEvent("popstate"));
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
          <div
            className="nav-group"
            data-group={group.label.toLowerCase()}
            key={group.label}
          >
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
        <Badge
          value={
            collapsed
              ? online
                ? "ONLINE"
                : "OFFLINE"
              : online
                ? "API ONLINE"
                : "API OFFLINE"
          }
        />
        <p>
          {online
            ? info?.hardware?.name
            : "Connect the backend to load verified state."}
        </p>
        <small>
          Worker:{" "}
          {online ? (info?.worker_online ? "online" : "offline") : "unknown"} ·{" "}
          {online ? (info?.queued_jobs ?? "--") : "--"} queued
        </small>
      </div>
      <div
        className="sidebar-resizer"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sidebar"
        aria-valuemin={68}
        aria-valuemax={maxWidth}
        aria-valuenow={collapsed ? 68 : sidebarWidth}
        tabIndex={0}
        title="Drag to resize sidebar (double-click to reset)"
        onMouseDown={startResize}
        onDoubleClick={() => {
          setCollapsed(false);
          setSidebarWidth?.(defaultWidth);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") {
            e.preventDefault();
            if (collapsed) {
              setCollapsed(false);
              setSidebarWidth?.(minWidth);
            } else {
              setSidebarWidth?.(Math.min(maxWidth, sidebarWidth + 16));
            }
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            if (!collapsed && sidebarWidth - 16 < minWidth) {
              setCollapsed(true);
            } else if (!collapsed) {
              setSidebarWidth?.(Math.max(minWidth, sidebarWidth - 16));
            }
          }
        }}
      />
    </aside>
  );
}
