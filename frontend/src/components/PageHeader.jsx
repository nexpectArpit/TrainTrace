import React from "react";
import { tabDescriptions, tabLabels } from "../app/config";
import DarkThemeSwitch from "./design-system/DarkThemeSwitch";
import WorkspaceContext from "./WorkspaceContext";

export default function PageHeader({
  workspace,
  tab,
  darkMode,
  setDarkMode,
  onSearch,
}) {
  return (
    <header className="page-header">
      <div className="page-header-title">
        <h1>{tabLabels[tab] || tab}</h1>
        <p className="page-description">{tabDescriptions[tab]}</p>
      </div>
      <div className="header-actions">
        {workspace && <WorkspaceContext workspace={workspace} inline />}
        <button
          type="button"
          className="header-search-btn"
          onClick={onSearch}
          aria-label="Search investigations, runs and models"
        >
          <svg
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            width="13"
            height="13"
            aria-hidden="true"
          >
            <circle cx="7" cy="7" r="4.5" />
            <path d="M10.5 10.5L14 14" />
          </svg>
          <span>Search</span>
        </button>
        <DarkThemeSwitch
          isDarkTheme={darkMode}
          setIsDarkTheme={(value) => setDarkMode(value)}
        />
      </div>
    </header>
  );
}
