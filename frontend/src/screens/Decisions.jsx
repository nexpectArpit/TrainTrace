import React, { useEffect, useState } from "react";
import { formatTime, fmt } from "../components/Common";
import { request } from "../services/api";
import {
  emptyDecision,
  Badge,
  Field,
  Select,
  Panel,
  Json,
  RequiredFieldLegend,
} from "../components/Common";
export default function Decisions({ workspace }) {
  const {
    online,
    setNotice,
    busy,
    decision,
    setDecision,
    run,
    act,
    expId,
    experiment,
    runs,
  } = workspace;
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [confirmFinal, setConfirmFinal] = useState(false);
  useEffect(() => setConfirmFinal(false), [run?.id]);
  const missingReasoning = [
    "limitations",
    "alternatives_considered",
    "why_not_alternative",
    "tradeoff_acknowledged",
  ].filter((key) => !String(decision[key] || "").trim());
  const reservedFinalRunId = experiment?.final_evaluation_run_id;
  const reservedFinalRun = runs?.find(
    (candidate) => candidate.id === reservedFinalRunId,
  );
  const canRecordDecision =
    run?.status === "COMPLETED" &&
    !!run.validation &&
    !reservedFinalRunId &&
    (!run.final_evaluation_status ||
      run.final_evaluation_status === "NOT_STARTED");
  const decisionUnavailableMessage = !run
    ? "Select a run from the workspace bar to record a decision."
    : run.status !== "COMPLETED"
      ? "Training must complete before you can record a candidate decision."
      : !run.validation
        ? "This run has no stored validation evidence, so a decision cannot be recorded."
        : reservedFinalRunId
          ? run.id === reservedFinalRunId
            ? "Decision entry is frozen because this run has used the investigation’s final test reservation. Its saved decision and result are below."
            : `Decision entry is frozen because the final test was reserved for ${reservedFinalRun?.approach_name || "another run"}. Open that run to review its result.`
          : "Decision entry is frozen because final test evaluation has been reserved.";
  return (
    <Panel
      title="Record a human decision"
      action={
        run?.decisions?.length > 0 && expId ? (
          <div className="actions">
            <a href={`/api/v1/experiments/${expId}/report`}>Decision report</a>
            <a href={`/api/v1/experiments/${expId}/report.csv`}>Metrics CSV</a>
          </div>
        ) : null
      }
    >
      <p>
        Choose a completed candidate using validation evidence. The final test
        partition stays sealed until a candidate is selected. Every decision
        preserves its evidence snapshot and reasoning.
      </p>
      {run && (
        <section
          className="decision-candidate-summary"
          aria-label="Candidate validation evidence"
        >
          <div>
            <span className="decision-summary-label">Run under review</span>
            <strong>{run.approach_name}</strong>
            <small>
              {run.model_architecture || "Architecture unknown"} ·{" "}
              {run.dataset?.name ||
                run.config?.dataset_name ||
                "Dataset unknown"}
            </small>
          </div>
          <div>
            <span className="decision-summary-label">
              Best validation accuracy
            </span>
            <strong>
              {run.best_val_accuracy == null
                ? "Unmeasured"
                : `${fmt(run.best_val_accuracy)}%`}
            </strong>
            <small>Validation split · not the final holdout</small>
          </div>
          <div>
            <span className="decision-summary-label">Final test</span>
            <strong>
              {run.final_evaluation_status === "COMPLETED"
                ? "Evaluated"
                : reservedFinalRunId
                  ? run.id === reservedFinalRunId
                    ? "Reserved for this run"
                    : "Reserved for another run"
                  : "Sealed"}
            </strong>
            <small>
              {reservedFinalRunId
                ? "One candidate per investigation"
                : "Available after selection"}
            </small>
          </div>
        </section>
      )}
      {canRecordDecision ? (
        <form
          className="decision-form"
          onInvalidCapture={() => setReasoningOpen(true)}
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
          <RequiredFieldLegend />
          <Select
            label="Decision status"
            value={decision.status}
            onChange={(v) => setDecision({ ...decision, status: v })}
            required
          >
            {[
              "CANDIDATE",
              "ACCEPTED",
              "REJECTED",
              "SUPERSEDED",
              "SELECTED",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </Select>
          <p className="decision-status-help">
            Candidate keeps the run under review. Select a candidate only after
            comparing validation evidence; that choice enables the
            investigation’s one final holdout evaluation.
          </p>
          <Field
            type="textarea"
            label="Decision rationale"
            required
            value={decision.rationale}
            onChange={(v) => setDecision({ ...decision, rationale: v })}
            placeholder="What validation evidence supports this decision?"
          />
          <details
            className="decision-reasoning-details"
            open={reasoningOpen}
            onToggle={(event) => setReasoningOpen(event.currentTarget.open)}
          >
            <summary>
              Reasoning details · limitations, alternatives and trade-offs{" "}
              {missingReasoning.length
                ? `(${missingReasoning.length} to complete)`
                : "(complete)"}
            </summary>
            <p>
              These fields preserve why this approach was chosen or rejected.
              Complete them before saving the decision.
            </p>
            <div className="grid two">
              {[
                [
                  "limitations",
                  "Observed limitations / strengths",
                  "What did validation reveal about failure cases or strengths?",
                ],
                [
                  "alternatives_considered",
                  "Alternative approaches considered",
                  "Which other runs or configurations did you compare?",
                ],
                [
                  "why_not_alternative",
                  "Why alternatives were not selected",
                  "What evidence ruled out the alternatives?",
                ],
                [
                  "tradeoff_acknowledged",
                  "Trade-offs accepted",
                  "What cost, speed, size or accuracy compromise are you accepting?",
                ],
              ].map(([key, label, placeholder]) => (
                <Field
                  key={key}
                  type="textarea"
                  label={label}
                  required
                  value={decision[key]}
                  onChange={(value) =>
                    setDecision({ ...decision, [key]: value })
                  }
                  placeholder={placeholder}
                />
              ))}
            </div>
            <Field
              type="textarea"
              label="Next investigation (optional)"
              value={decision.next_investigation}
              onChange={(value) =>
                setDecision({ ...decision, next_investigation: value })
              }
              placeholder="What should be tried next?"
            />
          </details>
          {missingReasoning.length > 0 && (
            <p className="decision-required-note" role="status">
              Complete the reasoning details before saving.
            </p>
          )}
          <button
            className="primary"
            disabled={
              busy ||
              !online ||
              run?.status !== "COMPLETED" ||
              !run?.validation ||
              !!reservedFinalRunId ||
              (run?.final_evaluation_status &&
                run.final_evaluation_status !== "NOT_STARTED") ||
              !String(decision.rationale || "").trim() ||
              missingReasoning.length > 0
            }
          >
            Save decision and evidence
          </button>
        </form>
      ) : (
        <div className="empty" role="status">
          {decisionUnavailableMessage}
        </div>
      )}
      {run?.latest_decision?.status === "SELECTED" && (
        <section className="record" aria-label="Final test evaluation">
          <h3>Final test evaluation</h3>
          {run.final_evaluation?.legacy_preselection_test_exposure ? (
            <p role="status">
              Historical test metrics exist from the old workflow. They were
              visible during candidate selection and cannot serve as a final
              result.
            </p>
          ) : run.final_evaluation ? (
            <p>
              Final holdout evaluation complete ·{" "}
              {fmt(run.final_evaluation.test_accuracy)}% accuracy
            </p>
          ) : (
            <>
              <p>
                This consumes the investigation’s one final test evaluation.
                Candidate decisions will be frozen once it is queued.
              </p>
              {!confirmFinal ? (
                <button
                  type="button"
                  className="primary"
                  disabled={
                    busy ||
                    !online ||
                    run.final_evaluation_status !== "NOT_STARTED" ||
                    !workspace.info?.worker_online
                  }
                  onClick={() => setConfirmFinal(true)}
                >
                  {run.final_evaluation_status === "NOT_STARTED"
                    ? "Run final test evaluation"
                    : `Final evaluation ${run.final_evaluation_status?.toLowerCase() || "queued"}`}
                </button>
              ) : (
                <div
                  className="final-evaluation-confirm"
                  role="group"
                  aria-label="Confirm final test reservation"
                >
                  <p>
                    <strong>
                      Reserve the final test for {run.approach_name}?
                    </strong>{" "}
                    This cannot be repeated for another candidate in this
                    investigation. Other decision entries will be frozen.
                  </p>
                  <button
                    type="button"
                    onClick={() => setConfirmFinal(false)}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="primary"
                    disabled={busy || !online || !workspace.info?.worker_online}
                    onClick={() =>
                      act(async () => {
                        const result = await request(
                          "/runs/final-evaluation",
                          "POST",
                          { run_id: run.id },
                        );
                        setConfirmFinal(false);
                        setNotice(
                          `Final test evaluation queued: ${result.job_id}`,
                        );
                        await workspace.refresh();
                      })
                    }
                  >
                    Confirm and queue final test
                  </button>
                </div>
              )}
            </>
          )}
        </section>
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
