import React from "react";
import { formatTime } from "../components/Common";
import { request } from "../services/api";
import {
  emptyDecision,
  Badge,
  Field,
  Select,
  Panel,
  Json,
} from "../components/Common";
export default function Decisions({ workspace }) {
  const {
    experiments,
    online,
    setNotice,
    busy,
    decision,
    setDecision,
    run,
    act,
    branch,
  } = workspace;
  return (
    <Panel title="Record a human decision">
      <p>
        Choose a completed, evaluated candidate. Every decision preserves its
        evidence snapshot and reasoning. Record “none” explicitly where no
        alternative or limitation applies.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(async () => {
            await request("/experiments/decisions", "POST", {
              ...decision,
              run_id: run.id,
            });
            setNotice("Decision and evidence snapshot saved.");
            setDecision(emptyDecision);
          });
        }}
      >
        <Select
          label="Decision status"
          value={decision.status}
          onChange={(v) => setDecision({ ...decision, status: v })}
        >
          {["CANDIDATE", "ACCEPTED", "REJECTED", "SUPERSEDED", "SELECTED"].map(
            (s) => (
              <option key={s}>{s}</option>
            ),
          )}
        </Select>
        {[
          ["rationale", "Decision rationale"],
          ["limitations", "Observed limitations / strengths"],
          ["alternatives_considered", "Alternative approaches considered"],
          ["why_not_alternative", "Why alternatives were not selected"],
          ["tradeoff_acknowledged", "Trade-offs accepted"],
          ["next_investigation", "Next investigation (optional)"],
        ].map(([k, l]) => (
          <Field
            key={k}
            type="textarea"
            label={l}
            required={k !== "next_investigation"}
            value={decision[k]}
            onChange={(v) => setDecision({ ...decision, [k]: v })}
          />
        ))}
        <button
          className="primary"
          disabled={
            busy || !online || run?.status !== "COMPLETED" || !run?.evaluation
          }
        >
          Save decision and evidence
        </button>
      </form>
      {run?.latest_decision && (
        <button onClick={() => branch(run)}>
          Investigate a successor approach →
        </button>
      )}
      {run?.decisions.map((d) => (
        <article key={d.id} className="record">
          <h3>
            <Badge value={d.status} /> {formatTime(d.timestamp)}
          </h3>
          <p>{d.rationale}</p>
          <Json
            data={{ analysis: d.details, evidence: d.evidence }}
            label="Decision details and frozen evidence"
          />
        </article>
      ))}
    </Panel>
  );
}
