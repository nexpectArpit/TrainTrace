import React from "react";
import { Select } from "./Common";

export default function WorkspaceContext({ workspace }) {
  const { tab, expId, runId, setRunId, experiments, runs, switchExperiment } =
    workspace;
  if (["Investigations", "Inference", "Search"].includes(tab)) return null;

  return (
    <div className="context-bar" aria-label="Current research context">
      <Select label="Investigation" value={expId} onChange={switchExperiment}>
        <option value="">Choose investigation</option>
        {experiments.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
            {item.archived ? " (archived)" : ""}
          </option>
        ))}
      </Select>
      {["Audits", "Decisions", "Training", "Registry"].includes(tab) && (
        <Select label="Run to inspect" value={runId} onChange={setRunId}>
          <option value="">Choose a run</option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {run.approach_name} · {run.status} · {run.id}
            </option>
          ))}
        </Select>
      )}
    </div>
  );
}
