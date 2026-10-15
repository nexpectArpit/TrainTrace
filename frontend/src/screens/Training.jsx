import React from "react";
import { formatTime } from "../components/Common";
import { request } from "../services/api";
import MetricChart from "../components/MetricChart";
import {
  activeStates,
  architectures,
  freshRun,
  fmt,
  Badge,
  Field,
  Select,
  Panel,
  Json,
} from "../components/Common";
export default function Training({ workspace }) {
  const {
    expId,
    setRunId,
    runs,
    info,
    online,
    error,
    setNotice,
    busy,
    setup,
    setSetup,
    live,
    events,
    experiment,
    run,
    act,
    metrics,
    executionStatus,
    stop,
  } = workspace;
  return (
    <>
      <Panel title="Configure an approach">
        <p>
          CIFAR-10 · 45,000 training / 5,000 validation / 10,000 holdout images.
          Jobs run sequentially. New runs capture provenance; legacy evidence
          remains unverified.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              await request("/runs/launch", "POST", {
                ...setup,
                experiment_id: expId,
              });
              setRunId(setup.run_id);
              setSetup(freshRun());
              setNotice("Run queued. Live state appears below.");
            });
          }}
        >
          <div className="grid two">
            <Field
              label="Run ID (unique)"
              value={setup.run_id}
              pattern="[A-Za-z0-9][A-Za-z0-9_-]{0,79}"
              onChange={(v) => setSetup({ ...setup, run_id: v })}
              required
            />
            <Field
              label="Approach name"
              value={setup.approach_name}
              onChange={(v) => setSetup({ ...setup, approach_name: v })}
              required
            />
          </div>
          <div className="grid three">
            <Select
              label="Architecture"
              value={setup.model_name}
              onChange={(v) =>
                setSetup({
                  ...setup,
                  model_name: v,
                  pretrained: v === "custom_cnn" ? false : setup.pretrained,
                })
              }
            >
              {architectures.map((a) => (
                <option key={a}>{a}</option>
              ))}
            </Select>
            <Select
              label="Optimizer"
              value={setup.optimizer}
              onChange={(v) => setSetup({ ...setup, optimizer: v })}
            >
              <option value="adamw">AdamW</option>
              <option value="sgd">SGD (momentum 0.9)</option>
            </Select>
            <Select
              label="Learning-rate schedule"
              value={setup.scheduler_type}
              onChange={(v) => setSetup({ ...setup, scheduler_type: v })}
            >
              {["constant", "cosine", "step"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </Select>
          </div>
          <div className="grid three">
            {[
              ["epochs", "Epochs", 1, 1000],
              ["batch_size", "Batch size", 2, 2048],
              ["learning_rate", "Learning rate", 0.000000001, 1],
              ["seed", "Initialization seed", 0, 4294967295],
              ["split_seed", "Dataset split seed", 0, 4294967295],
              ["weight_decay", "Weight decay", 0, 1],
            ].map(([k, l, min, max]) => (
              <Field
                key={k}
                label={l}
                type="number"
                step={
                  ["learning_rate", "weight_decay"].includes(k) ? "any" : "1"
                }
                min={min}
                max={max}
                required
                value={setup[k]}
                onChange={(v) => setSetup({ ...setup, [k]: v })}
              />
            ))}
          </div>
          <label className="check">
            <input
              type="checkbox"
              disabled={setup.model_name === "custom_cnn"}
              checked={setup.pretrained}
              onChange={(e) =>
                setSetup({ ...setup, pretrained: e.target.checked })
              }
            />
            Initialize with ImageNet weights (first use needs a download)
          </label>
          <Select
            label="Predecessor run / motivating limitation"
            value={setup.predecessor_run_id || ""}
            onChange={(v) =>
              setSetup({ ...setup, predecessor_run_id: v || null })
            }
          >
            <option value="">Initial approach</option>
            {runs
              .filter((r) => r.latest_decision)
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.approach_name}
                </option>
              ))}
          </Select>
          <Field
            label="Why investigate this approach?"
            type="textarea"
            value={setup.motivating_reason}
            required={!!setup.predecessor_run_id}
            onChange={(v) => setSetup({ ...setup, motivating_reason: v })}
          />
          <button
            className="primary"
            disabled={
              busy ||
              !online ||
              !experiment ||
              !!experiment.archived ||
              !info?.worker_online
            }
          >
            Queue training run
          </button>
        </form>
      </Panel>
      <Panel
        title="Execution and durable metrics"
        action={
          run &&
          activeStates.includes(executionStatus) && (
            <button
              className="danger"
              disabled={busy}
              onClick={() => stop(run.id)}
            >
              Stop run
            </button>
          )
        }
      >
        {!run ? (
          <div className="empty">
            Choose an existing run to inspect its execution.
          </div>
        ) : (
          <>
            <div className="metric-strip">
              <div>
                <small>Execution</small>
                <Badge value={executionStatus} />
              </div>
              <div>
                <small>Epochs persisted</small>
                <strong>
                  {metrics.length} / {run.epochs}
                </strong>
              </div>
              <div>
                <small>Best validation accuracy</small>
                <strong>{fmt(run.best_val_accuracy)}%</strong>
              </div>
              <div>
                <small>Elapsed epoch time</small>
                <strong>{fmt(run.total_duration_sec, 1)} s</strong>
              </div>
            </div>
            {live?.progress && (
              <p>
                Epoch {live.progress.epoch}, batch {live.progress.batch_idx} /{" "}
                {live.progress.total_batches} · current LR {live.progress.lr} ·
                batch training accuracy {fmt(live.progress.running_acc)}%
              </p>
            )}
            {activeStates.includes(executionStatus) && (
              <progress
                aria-label="Completed epochs"
                value={metrics.length}
                max={run.epochs}
              />
            )}
            {run.error && <pre className="error">{run.error}</pre>}
            <div className="grid two">
              <MetricChart
                runs={[{ ...run, metrics }]}
                field="val_acc"
                title="Validation accuracy (%)"
              />
              <MetricChart
                runs={[{ ...run, metrics }]}
                field="val_loss"
                title="Validation loss"
              />
            </div>
            <div className="table-wrap">
              <table>
                <caption>Persisted epoch metrics</caption>
                <thead>
                  <tr>
                    {[
                      "Epoch",
                      "Train loss",
                      "Train acc %",
                      "Val loss",
                      "Val acc %",
                      "LR",
                      "Seconds",
                    ].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => (
                    <tr key={m.id}>
                      <td>{m.epoch}</td>
                      <td>{fmt(m.train_loss, 4)}</td>
                      <td>{fmt(m.train_acc)}</td>
                      <td>{fmt(m.val_loss, 4)}</td>
                      <td>{fmt(m.val_acc)}</td>
                      <td>{m.learning_rate ?? "Unknown"}</td>
                      <td>{fmt(m.epoch_time_sec, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details>
              <summary>Execution events (latest 300)</summary>
              <div className="events">
                {events.length
                  ? events.map((e) => (
                      <p key={e.id}>
                        {formatTime(e.created_at)} · {e.message}
                      </p>
                    ))
                  : "No recorded events. Legacy timestamps are not reconstructed."}
              </div>
            </details>
            <Json
              data={{
                configuration: run.config,
                dataset: run.dataset,
                environment: run.environment,
              }}
              label="Configuration and historical provenance"
            />
            <h3>Artifacts</h3>
            {run.artifacts.length ? (
              <ul>
                {run.artifacts.map((a) => (
                  <li key={a.id}>
                    <a href={`/api/v1/runs/artifacts/${a.id}`}>{a.kind}</a> ·{" "}
                    {(a.size_bytes / 1024).toFixed(1)} KB{" "}
                    <small>SHA256 {a.sha256}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No catalogued artifacts. Legacy files were preserved.</p>
            )}
          </>
        )}
      </Panel>
    </>
  );
}
