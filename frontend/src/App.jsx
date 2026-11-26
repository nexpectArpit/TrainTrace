import React, { useEffect, useState } from "react";
import useTheme from "./hooks/useTheme";
import useWorkspace from "./app/useWorkspace";
import AppSidebar from "./components/AppSidebar";
import PageHeader from "./components/PageHeader";
import {
  WorkspaceMessages,
  WorkspaceFooter,
} from "./components/WorkspaceMessages";
import WorkspaceScreen from "./components/WorkspaceScreen";

const SIDEBAR_MIN = 190;
const SIDEBAR_MAX = 360;
const SIDEBAR_DEFAULT = 244;
const SIDEBAR_COLLAPSED = 68;

export default function App() {
  const workspace = useWorkspace();
  const { tab, online, jobs, connectionError } = workspace;
  const [darkMode, setDarkMode] = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("traintrace-sidebar") === "collapsed",
  );
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(localStorage.getItem("traintrace-sidebar-width"));
    return Number.isFinite(saved) &&
      saved >= SIDEBAR_MIN &&
      saved <= SIDEBAR_MAX
      ? saved
      : SIDEBAR_DEFAULT;
  });
  const [sidebarResizing, setSidebarResizing] = useState(false);

  useEffect(() => {
    localStorage.setItem(
      "traintrace-sidebar",
      sidebarCollapsed ? "collapsed" : "expanded",
    );
  }, [sidebarCollapsed]);

  useEffect(() => {
    localStorage.setItem("traintrace-sidebar-width", String(sidebarWidth));
  }, [sidebarWidth]);

  return (
    <div
      className={`app-shell${darkMode ? " theme-dark" : ""}${sidebarCollapsed ? " sidebar-collapsed" : ""}${sidebarResizing ? " sidebar-resizing" : ""}`}
      style={{
        "--sidebar-width": `${sidebarCollapsed ? SIDEBAR_COLLAPSED : sidebarWidth}px`,
      }}
    >
      <AppSidebar
        workspace={workspace}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        sidebarWidth={sidebarWidth}
        setSidebarWidth={setSidebarWidth}
        setSidebarResizing={setSidebarResizing}
        minWidth={SIDEBAR_MIN}
        maxWidth={SIDEBAR_MAX}
        defaultWidth={SIDEBAR_DEFAULT}
      />
      <main id="main" tabIndex={-1}>
        <PageHeader
          workspace={workspace}
          tab={tab}
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          onSearch={() => workspace.setTab("Search")}
        />
        <WorkspaceMessages
          workspace={workspace}
          connectionError={connectionError}
        />
        <WorkspaceScreen workspace={workspace} />
        <WorkspaceFooter online={online} jobs={jobs} />
      </main>
    </div>
  );
}
