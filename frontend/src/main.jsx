import React from "react";
import ReactDOM from "react-dom/client";
import Entry from "./app/Entry";

import "./styles/index.css";
import "./styles/mlflow-design.css";
import "./styles/decisions.css";
import "./styles/workflow-evidence.css";
import "./styles/compare.css";
import "./styles/registry.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Entry />
  </React.StrictMode>,
);
