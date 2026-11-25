import { useEffect, useState } from "react";

export default function useTheme() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem("traintrace-theme");
    return saved
      ? saved === "dark"
      : Boolean(window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  });
  useEffect(() => {
    localStorage.setItem("traintrace-theme", darkMode ? "dark" : "light");
    document.body.classList.toggle("traintrace-dark", darkMode);
    document.documentElement.style.colorScheme = darkMode ? "dark" : "light";
    const favicon = document.getElementById("traintrace-favicon");
    if (favicon)
      favicon.href = darkMode ? "/favicon-dark.png" : "/favicon-light.png";
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", darkMode ? "#101719" : "#f5f7f8");
  }, [darkMode]);
  return [darkMode, setDarkMode];
}
