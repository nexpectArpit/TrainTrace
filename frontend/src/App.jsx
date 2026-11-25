import React, { useEffect, useState } from "react";
import useTheme from "./hooks/useTheme";
import useWorkspace from "./app/useWorkspace";
import AppSidebar from "./components/AppSidebar";
import PageHeader from "./components/PageHeader";
import WorkspaceContext from "./components/WorkspaceContext";
import {
  WorkspaceMessages,
  WorkspaceFooter,
} from "./components/WorkspaceMessages";
import WorkspaceScreen from "./components/WorkspaceScreen";

export default function App() {
  const workspace = useWorkspace();
  const { tab, online, jobs, connectionError } = workspace;
  const [darkMode, setDarkMode] = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("traintrace-sidebar") === "collapsed",
  );

  useEffect(() => {
    localStorage.setItem(
      "traintrace-sidebar",
      sidebarCollapsed ? "collapsed" : "expanded",
    );
  }, [sidebarCollapsed]);

  return (
    <div
      className={`app-shell${darkMode ? " theme-dark" : ""}${sidebarCollapsed ? " sidebar-collapsed" : ""}`}
    >
      <AppSidebar
        workspace={workspace}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
      />
      <main id="main" tabIndex={-1}>
        <PageHeader
          tab={tab}
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          onSearch={() => workspace.setTab("Search")}
        />
        <WorkspaceMessages
          workspace={workspace}
          connectionError={connectionError}
        />
        <WorkspaceContext workspace={workspace} />
        <WorkspaceScreen workspace={workspace} />
        <WorkspaceFooter online={online} jobs={jobs} />
      </main>
    </div>
  );
}
