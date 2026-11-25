import React from "react";
import { request } from "../services/api";
import {
  activeStates,
  fmt,
  Badge,
  Field,
  Panel,
  Json,
  canShowFinalEvaluation,
} from "../components/Common";
export default function Audits({ workspace }) {
  const {
    runs,
    info,
    online,
    error,
    setNotice,
    busy,
    seeds,
    setSeeds,
    run,
    act,
    stop,
  } = workspace;
  const rawProtocolSeeds = seeds.split(",").map((seed) => seed.trim());
  const parsedProtocolSeeds = rawProtocolSeeds.map(Number);
  const protocolSeedsValid =
    rawProtocolSeeds.length > 0 &&
    rawProtocolSeeds.every((seed) => /^\d+$/.test(seed)) &&
    parsedProtocolSeeds.every(
      (seed) => Number.isInteger(seed) && seed >= 0 && seed <= 4294967295,
    ) &&
    new Set(parsedProtocolSeeds).size === parsedProtocolSeeds.length;
  const queueBlockedReason = !online
    ? "Connect to the backend to queue a reproducibility check."
    : !run
      ? "Choose a completed source run first."
      : run.status !== "COMPLETED"
        ? "The source run must finish before it can be replayed."
        : !run.config || !run.validation
          ? "This run has no complete saved configuration and validation evidence."
          : !info?.worker_online
            ? "The training worker is offline. Restart the backend before queuing replays."
            : "";
  return (
    <>
      <Panel title="Run evidence">
        {run?.validation ? (
          <>
            <div className="metric-strip">
              {[
                [
                  "Validation accuracy",
                  run.validation.validation_accuracy,
                  "%",
                ],
                ["Validation loss", run.validation.validation_loss, ""],
                ["Selected epoch", run.validation.checkpoint_epoch, ""],
              ].map(([k, v, u]) => (
                <div key={k}>
                  <small>{k}</small>
                  <strong>
                    {k === "Selected epoch" ? (v ?? "—") : fmt(v, 4)}
                    {u}
                  </strong>
                </div>
              ))}
            </div>
            <Json
              data={{
                validation: run.validation,
                final_test: canShowFinalEvaluation(run)
                  ? run.final_evaluation
                  : null,
              }}
              label="Validation evidence and (if selected) final test evaluation"
            />
            <p className="panel-intro" role="status">
              {canShowFinalEvaluation(run)
                ? "Post-selection final test evaluation is complete."
                : run.final_evaluation?.legacy_preselection_test_exposure
                  ? "Legacy test results are withheld because they were exposed before candidate selection."
                  : run.latest_decision?.status === "SELECTED"
                    ? `Final test evaluation ${run.final_evaluation_status?.toLowerCase() || "pending"}.`
                    : "The final test split remains sealed until this run is selected."}
            </p>
          </>
        ) : (
          <div className="empty">
            Choose a completed run with captured validation evidence. The test
            partition remains sealed until selection.
          </div>
        )}
      </Panel>
      <Panel title="Reproducibility protocols">
        <p>
          These optional checks replay the saved configuration. They do not open
          the final test split.
        </p>
        {queueBlockedReason && (
          <p className="queue-disabled-reason" role="status">
            {queueBlockedReason}
          </p>
        )}
        <div className="audit-protocol-intro">
          <strong>Protocol A · repeatability</strong>
          <p>
            Repeat the same run twice with its original seed. Compare both
            replays with the source run under matching conditions.
          </p>
        </div>
        <div className="actions">
          <button
            type="button"
            disabled={busy || !!queueBlockedReason}
            onClick={() =>
              act(async () => {
                const result = await request("/runs/audit/protocol-a", "POST", {
                  run_id: run.id,
                });
                setNotice(`Protocol A queued: ${result.job_id}`);
              })
            }
          >
            Queue Protocol A
          </button>
        </div>
        <details className="audit-seed-protocol">
          <summary>Protocol B · seed sensitivity</summary>
          <p>
            Vary the run seed while keeping the dataset split fixed. The result
            measures sensitivity across the chosen seeds.
          </p>
          <Field
            label="Run seeds (unique integers)"
            value={seeds}
            info="Comma-separated whole numbers from 0 to 4294967295. The original data split seed remains fixed."
            aria-invalid={!protocolSeedsValid}
            onChange={setSeeds}
          />
          {!protocolSeedsValid && (
            <p className="queue-disabled-reason" role="status">
              Use unique whole-number seeds from 0 to 4294967295, separated by
              commas.
            </p>
          )}
          <button
            type="button"
            disabled={busy || !!queueBlockedReason || !protocolSeedsValid}
            onClick={() =>
              act(async () => {
                const result = await request("/runs/audit/protocol-b", "POST", {
                  run_id: run.id,
                  seeds: parsedProtocolSeeds,
                });
                setNotice(`Protocol B queued: ${result.job_id}`);
              })
            }
          >
            Queue Protocol B
          </button>
        </details>
        {run?.audits.map((a) => (
          <article className="record" key={a.id}>
            <h3>
              Protocol {a.protocol} <Badge value={a.status} />
            </h3>
            <code>{a.id}</code>
            {!!a.members?.length && (
              <p>
                {a.members.filter((m) => m.status === "COMPLETED").length}{" "}
                replay runs completed
              </p>
            )}
            {!!a.members?.length && (
              <ul className="audit-member-list">
                {a.members.map((member) => (
                  <li key={member.id}>
                    <code>{member.id}</code> · seed {member.seed} ·{" "}
                    <Badge value={member.status} />
                    {member.error && (
                      <span className="error">{member.error}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {a.report ? (
              <>
                <p>
                  {a.protocol === "A"
                    ? `${a.report.passed ? "PASS" : "MISMATCH"} · ${a.report.reason}`
                    : `Mean ${fmt(a.report.mean_accuracy)}% · Std ${fmt(a.report.std_deviation)} · Min ${fmt(a.report.min_accuracy)}% · Max ${fmt(a.report.max_accuracy)}% · Spread ${fmt(a.report.spread)} pp`}
                </p>
                {a.protocol === "B" && a.report.environment_match === false && (
                  <p className="error">
                    Execution environment differs from the source run. Treat
                    this study as exploratory.
                  </p>
                )}
                <Json
                  data={a.report}
                  label="Persisted audit report and participating runs"
                />
              </>
            ) : (
              <p>
                {a.error ||
                  "Report becomes available after all participating runs complete."}
              </p>
            )}
            {activeStates.includes(a.status) && (
              <button onClick={() => stop(a.id)} disabled={busy || !online}>
                Stop audit
              </button>
            )}
          </article>
        ))}
      </Panel>
    </>
  );
}
