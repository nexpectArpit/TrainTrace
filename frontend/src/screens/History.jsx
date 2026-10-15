import React from "react";
import { fmt, Badge, Panel, Json } from "../components/Common";
export default function History({ workspace }) {
  const { setTab, expId, setRunId, experiments, runs, decision, run, branch } =
    workspace;
  return (
    <Panel
      title="Investigation reasoning chain"
      action={
        expId && (
          <a href={`/api/v1/experiments/${expId}/report`}>Download report</a>
        )
      }
    >
      <p>
        Follow explicit predecessor links and inspect the reasoning behind each
        approach. Missing historical fields remain unknown.
      </p>
      {[...runs].reverse().map((r) => (
        <article className="record history" key={r.id}>
          <div className="eyebrow">
            {r.predecessor_run_id
              ? `SUCCESSOR OF ${r.predecessor_run_id}`
              : "INITIAL APPROACH / NO PREDECESSOR RECORDED"}
          </div>
          <h3>
            {r.approach_name}{" "}
            <Badge value={r.latest_decision?.status || "CANDIDATE"} />
          </h3>
          <p>
            {r.motivating_reason ||
              "Motivation not recorded (legacy or initial run)."}
          </p>
          <p>
            Run {r.id} · holdout {fmt(r.evaluation?.test_accuracy)}% ·{" "}
            {r.decisions.length} decisions
          </p>
          {r.latest_decision && (
            <>
              <p>{r.latest_decision.rationale}</p>
              <Json
                data={{
                  decisions: r.decisions,
                  evaluation: r.evaluation,
                }}
                label="Evidence, limitations, alternatives and complete decision history"
              />
            </>
          )}
          <button
            onClick={() => {
              setRunId(r.id);
              setTab("Decisions");
            }}
          >
            Review candidate
          </button>
          {r.latest_decision && (
            <button onClick={() => branch(r)}>Branch from this approach</button>
          )}
        </article>
      ))}
      {!runs.length && (
        <div className="empty">
          No approaches recorded in this investigation.
        </div>
      )}
    </Panel>
  );
}
