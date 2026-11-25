import React from "react";
import { activeStates } from "./Common";
import { tabLabels } from "../app/config";
import "./WorkflowNavigation.css";

export default function WorkflowNavigation({ workspace }) {
  const {
    tab,
    setTab,
    setRunId,
    experiment,
    runs,
    run,
    models,
    activeModel,
    executionStatus,
    busy,
    branch,
  } = workspace;
  const completed = runs.some((item) => item.status === "COMPLETED");
  const firstCompletedRun = runs.find(
    (item) => item.status === "COMPLETED" && item.validation,
  );
  const reservedRun = runs.find(
    (item) => item.id === experiment?.final_evaluation_run_id,
  );
  const release = models.find((item) => item.run_id === run?.id);
  let back,
    next,
    message,
    blocked = false;
  switch (tab) {
    case "Investigations":
      next = "Training";
      blocked = !experiment || !!experiment.archived;
      message = blocked
        ? "Create or open an active investigation to configure a training run."
        : runs.length
          ? `This investigation has ${runs.length} recorded ${runs.length === 1 ? "run" : "runs"}. Continue an approach or open one to inspect its evidence.`
          : "Next: configure and queue your first approach.";
      break;
    case "Training":
      back = "Investigations";
      next = "Compare";
      blocked = !completed;
      message = blocked
        ? "Wait for a run to complete before comparing validation results."
        : "Next: compare validation results and try completed checkpoints on your own image.";
      break;
    case "Compare":
      back = "Training";
      next = "Decisions";
      blocked = run?.status !== "COMPLETED" || !run?.validation;
      message = blocked
        ? "Choose a completed run with validation evidence in ‘Run to inspect’ before recording its decision."
        : `Try candidate checkpoints on an image here, then record your reasoning for ${run.approach_name}. Repeatability checks are optional.`;
      break;
    case "Audits":
      back = "Compare";
      next = "Decisions";
      blocked = run?.status !== "COMPLETED" || !run?.validation;
      message = blocked
        ? "Choose a completed run with validation evidence to run an optional repeatability check."
        : "Review repeatability evidence if useful, then record a decision for this run.";
      break;
    case "Decisions":
      back = "Compare";
      next = "Registry";
      blocked =
        run?.latest_decision?.status !== "SELECTED" ||
        run?.final_evaluation_status !== "COMPLETED";
      message = !run
        ? "Choose a completed run with validation evidence to record a decision."
        : run.status !== "COMPLETED"
          ? "This run did not complete. Open a completed run with validation evidence to continue."
          : experiment?.final_evaluation_run_id &&
              experiment.final_evaluation_run_id !== run.id
            ? `The final test is reserved for ${reservedRun?.approach_name || "another run"}. Open that run to review its result; decisions here are frozen.`
            : run.latest_decision?.status !== "SELECTED"
              ? "Record a decision from validation evidence. Select one candidate only if you want to unseal the final test set."
              : run.final_evaluation_status !== "COMPLETED"
                ? "The selected candidate must finish its one final test evaluation before optional release registration."
                : "Your decision and final test are complete. Registration is optional; use it to make an immutable release for serving.";
      break;
    case "Registry":
      back = "Decisions";
      blocked = !release || release.id !== activeModel;
      message = !release
        ? "Register a selected candidate if you need a named, immutable model version. Candidate image testing is available in Compare."
        : blocked
          ? "Activate a registered release above to use stable serving below."
          : "The active release can serve image predictions below.";
      break;
    case "Inference":
      back = "Registry";
      message =
        "Review predictions. Return to Registry to change the active model, or investigate another approach.";
      break;
    case "History":
      back = "Investigations";
      next = "Training";
      blocked = !experiment || !!experiment.archived;
      message =
        "Review previous reasoning, then return to Training to investigate an approach.";
      break;
    case "Search":
      back = "Investigations";
      message =
        "Open a search result to continue work on its investigation or run.";
      break;
    default:
      return null;
  }
  const go = (page) => {
    setTab(page);
    requestAnimationFrame(() => {
      const main = document.getElementById("main");
      main?.focus();
      main?.scrollIntoView({ block: "start" });
    });
  };
  const canIterate =
    ["Compare", "Decisions", "History", "Registry", "Inference"].includes(
      tab,
    ) &&
    run &&
    !activeStates.includes(executionStatus) &&
    !experiment?.archived;
  return (
    <nav className="workflow-navigation" aria-label="Next steps">
      <p role="status">{message}</p>
      <div className="workflow-navigation-actions">
        {back && (
          <button type="button" onClick={() => go(back)}>
            ← Back to {tabLabels[back] || back}
          </button>
        )}
        {tab === "Decisions" && reservedRun && reservedRun.id !== run?.id && (
          <button type="button" onClick={() => setRunId(reservedRun.id)}>
            Open selected run
          </button>
        )}
        {tab === "Decisions" &&
          !reservedRun &&
          run?.status !== "COMPLETED" &&
          firstCompletedRun && (
            <button
              type="button"
              onClick={() => setRunId(firstCompletedRun.id)}
            >
              Open completed run
            </button>
          )}
        {canIterate && (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              branch(run);
              go("Training");
            }}
          >
            Investigate another approach
          </button>
        )}
        {tab === "Compare" && (
          <button type="button" onClick={() => go("Audits")}>
            Optional: Reproducibility
          </button>
        )}
        {next && (
          <button
            type="button"
            className="primary"
            disabled={busy || blocked}
            onClick={() => go(next)}
          >
            {tab === "Decisions"
              ? "Optional: Register model"
              : `Next: ${tabLabels[next] || next} →`}
          </button>
        )}
      </div>
    </nav>
  );
}
