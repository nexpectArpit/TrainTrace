import React from "react";
import { Panel } from "../components/Common";
import InvestigationTimeline from "../components/InvestigationTimeline";

export default function History({ workspace }) {
  const { expId, runs, setRunId, setTab, branch } = workspace;
  return (
    <Panel
      title="Investigation timeline"
      action={
        expId && (
          <div className="actions">
            <a href={`/api/v1/experiments/${expId}/report`}>Decision report</a>
            <a href={`/api/v1/experiments/${expId}/report.csv`}>Metrics CSV</a>
          </div>
        )
      }
    >
      <InvestigationTimeline
        runs={runs}
        onOpenRun={(run) => {
          setRunId(run.id);
          setTab("Training");
        }}
        onBranch={branch}
      />
    </Panel>
  );
}
