import React from "react";
import { tabDescriptions, tabLabels } from "../app/config";
import DarkThemeSwitch from "./design-system/DarkThemeSwitch";

export default function PageHeader({ tab, darkMode, setDarkMode, onSearch }) {
  return (
    <header className="page-header">
      <div>
        <h1>{tabLabels[tab] || tab}</h1>
        <p className="page-description">{tabDescriptions[tab]}</p>
      </div>
      <div className="header-actions">
        <button
          type="button"
          onClick={onSearch}
          aria-label="Search investigations, runs and models"
        >
          Search
        </button>
        <DarkThemeSwitch
          isDarkTheme={darkMode}
          setIsDarkTheme={(value) => setDarkMode(value)}
        />
      </div>
    </header>
  );
}
