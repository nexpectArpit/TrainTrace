import React from "react";

export function WorkspaceMessages({ workspace, connectionError }) {
  const { notice, error, setError } = workspace;
  return (
    <>
      <div aria-live="polite" aria-atomic="true">
        {notice && <div className="notice">{notice}</div>}
      </div>
      {connectionError && (
        <div className="error" role="alert" aria-live="assertive">
          {connectionError}
        </div>
      )}
      {error && (
        <div className="error" role="alert" aria-live="assertive">
          {error}
          <button aria-label="Dismiss error" onClick={() => setError("")}>
            ×
          </button>
        </div>
      )}
    </>
  );
}

export function WorkspaceFooter({ online, jobs }) {
  return (
    <footer>
      TrainTrace · Local single-user workspace ·{" "}
      {online
        ? `${jobs.filter((job) => job.status === "RUNNING").length} active job, ${jobs.filter((job) => job.status === "QUEUED").length} queued`
        : "Backend unavailable"}{" "}
      · Missing evidence is shown as unknown.
    </footer>
  );
}
