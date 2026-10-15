import React from "react";
import { request } from "../services/api";
import {
  activeStates,
  fmt,
  Badge,
  Field,
  Panel,
  Json,
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
  return (
    <>
      <Panel title="Holdout evaluation">
        {run?.evaluation ? (
          <>
            <div className="metric-strip">
              {[
                ["Test accuracy", run.evaluation.test_accuracy, "%"],
                ["Test loss", run.evaluation.test_loss, ""],
                ["Macro precision", run.evaluation.precision_macro, ""],
                ["Macro recall", run.evaluation.recall_macro, ""],
                ["Macro F1", run.evaluation.f1_macro, ""],
              ].map(([k, v, u]) => (
                <div key={k}>
                  <small>{k}</small>
                  <strong>
                    {fmt(v, 4)}
                    {u}
                  </strong>
                </div>
              ))}
            </div>
            <Json
              data={run.evaluation}
              label="Confusion matrix, artifact identity and latency methodology"
            />
          </>
        ) : (
          <div className="empty">
            Choose a completed run with captured holdout evaluation. Legacy
            validation scores are not test evidence.
          </div>
        )}
      </Panel>
      <Panel title="Reproducibility protocols">
        <p>
          Audits replay the original full configuration through the same queue.
          Protocol A compares two replays with the original under matching
          conditions. Protocol B varies initialization seeds while holding the
          split fixed.
        </p>
        <Field
          label="Protocol B seeds (unique integers)"
          value={seeds}
          onChange={setSeeds}
        />
        <div className="actions">
          {["A", "B"].map((p) => (
            <button
              key={p}
              disabled={
                busy ||
                !online ||
                run?.status !== "COMPLETED" ||
                !run?.config ||
                !run?.evaluation ||
                !info?.worker_online
              }
              onClick={() =>
                act(async () => {
                  const parsed = seeds.split(",").map((s) => Number(s.trim()));
                  if (
                    seeds.split(",").some((s) => !s.trim()) ||
                    parsed.some((n) => !Number.isInteger(n))
                  )
                    throw new Error("Enter comma-separated integer seeds.");
                  const result = await request(
                    `/runs/audit/protocol-${p.toLowerCase()}`,
                    "POST",
                    { run_id: run.id, seeds: parsed },
                  );
                  setNotice(`Protocol ${p} queued: ${result.job_id}`);
                })
              }
            >
              Queue Protocol {p}
            </button>
          ))}
        </div>
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
            <Json data={a.members} label="Replay run progress and failures" />
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
              <button onClick={() => stop(a.id)} disabled={busy}>
                Stop audit
              </button>
            )}
          </article>
        ))}
      </Panel>
    </>
  );
}
