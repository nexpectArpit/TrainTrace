import React from "react";
import {
  formatTime,
  activeStates,
  fmt,
  Badge,
  Panel,
  Json,
} from "../../components/Common";
import {
  estimateTraining,
  formatDuration,
} from "../../services/trainingEstimate";
import NotebookGuide from "../../components/NotebookGuide";
import LiveMetricsDashboard from "./LiveMetricsDashboard";

export default function RunExecutionPanel({ workspace }) {
  const {
    run,
    live,
    liveSamples,
    events,
    metrics,
    executionStatus,
    busy,
    online,
    liveError,
    stop,
  } = workspace;
  const runInProgress = activeStates.includes(executionStatus);
  const [nowMs, setNowMs] = React.useState(() => Date.now());
  React.useEffect(() => {
    if (!runInProgress) return undefined;
    setNowMs(Date.now());
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [runInProgress]);
  const timeEstimate = estimateTraining(metrics, run?.epochs);
  const latestPreparationEvent = [...events]
    .reverse()
    .find((item) =>
      /preparing .*dataset|loading .*(dataset|cifar|mnist|svhn)/i.test(
        item.message || "",
      ),
    );
  const preparationName = latestPreparationEvent?.message?.match(
    /(?:Preparing|Loading)\s+([^.;]+)/i,
  )?.[1];
  const stageProgress = live?.progress;
  const phase = stageProgress?.phase || "";
  const isCloudRun =
    run?.execution_target === "kaggle" ||
    stageProgress?.provider === "Kaggle Cloud GPU" ||
    phase.startsWith("cloud_") ||
    events.some((item) => /kaggle/i.test(item.message || ""));
  const isPreparingDataset =
    runInProgress &&
    metrics.length === 0 &&
    (phase === "dataset_preparation" ||
      (!stageProgress && Boolean(latestPreparationEvent)));
  const isWaitingIndeterminate =
    runInProgress &&
    metrics.length === 0 &&
    (isPreparingDataset ||
      phase.startsWith("cloud_") ||
      executionStatus === "QUEUED" ||
      !stageProgress);
  const pipelineSteps = React.useMemo(() => {
    if (!runInProgress) return [];
    if (isCloudRun) {
      const remoteStatus = String(
        stageProgress?.remote_status || "",
      ).toUpperCase();
      let activeIndex = 0;
      if (phase === "cloud_ingest" || remoteStatus === "COMPLETE") {
        activeIndex = 3;
      } else if (
        phase === "cloud_running" ||
        phase === "training" ||
        phase === "validation" ||
        remoteStatus === "RUNNING" ||
        metrics.length > 0
      ) {
        activeIndex = 2;
      } else if (
        phase === "cloud_startup" ||
        remoteStatus === "SUBMITTED" ||
        remoteStatus === "QUEUED" ||
        executionStatus === "QUEUED"
      ) {
        activeIndex = 1;
      }
      return [
        { key: "dispatch", label: "Dispatched" },
        { key: "queue", label: "Kaggle Queue" },
        { key: "gpu", label: "T4 GPU Training" },
        { key: "sync", label: "Sync Artifacts" },
      ].map((step, index) => ({
        ...step,
        state:
          index < activeIndex
            ? "done"
            : index === activeIndex
              ? "active"
              : "pending",
      }));
    }
    let activeIndex = 0;
    if (metrics.length >= (run?.epochs || 1)) {
      activeIndex = 3;
    } else if (
      phase === "training" ||
      phase === "validation" ||
      metrics.length > 0
    ) {
      activeIndex = 2;
    } else if (phase === "model_init") {
      activeIndex = 1;
    }
    return [
      { key: "dataset", label: "Dataset" },
      { key: "init", label: "Model Init" },
      { key: "train", label: "Train & Eval" },
      { key: "finalize", label: "Finalize" },
    ].map((step, index) => ({
      ...step,
      state:
        index < activeIndex
          ? "done"
          : index === activeIndex
            ? "active"
            : "pending",
    }));
  }, [
    runInProgress,
    isCloudRun,
    phase,
    stageProgress?.remote_status,
    metrics.length,
    executionStatus,
    run?.epochs,
  ]);
  const imageArtifacts =
    run?.artifacts?.filter(
      (artifact) =>
        [
          "dataset_preview_png",
          "training_curves_png",
          "confusion_matrix_png",
        ].includes(artifact.kind) &&
        !(artifact.kind === "training_curves_png" && metrics.length > 0),
    ) || [];
  const downloadPercent =
    stageProgress?.download_total_bytes > 0
      ? Math.min(
          100,
          Math.round(
            (100 * (stageProgress.downloaded_bytes || 0)) /
              stageProgress.download_total_bytes,
          ),
        )
      : null;
  const fallbackEvent = latestPreparationEvent || events[events.length - 1];
  const eventTimestamp = fallbackEvent?.created_at;
  const eventStartedAt = eventTimestamp
    ? Date.parse(
        eventTimestamp.includes("T")
          ? eventTimestamp
          : `${eventTimestamp.replace(" ", "T")}Z`,
      ) / 1000
    : Number.NaN;
  const runStartedAt = run?.created_at
    ? Date.parse(
        run.created_at.includes("T")
          ? run.created_at
          : `${run.created_at.replace(" ", "T")}Z`,
      ) / 1000
    : Number.NaN;
  const anchorSeconds =
    stageProgress?.started_at ||
    (Number.isFinite(runStartedAt) ? runStartedAt : eventStartedAt);
  const elapsedSeconds = runInProgress
    ? Math.max(0, Math.floor(nowMs / 1000 - (anchorSeconds || nowMs / 1000)))
    : 0;
  const formatElapsed = (seconds) =>
    `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return (
    <Panel
      title="Execution and durable metrics"
      action={
        run &&
        activeStates.includes(executionStatus) && (
          <button
            className="danger"
            disabled={busy || !online || live?.cancel_requested}
            onClick={() => stop(run.id)}
          >
            {live?.cancel_requested ? "Stopping…" : "Stop run"}
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
              <small>Recorded epoch time</small>
              <strong>
                {metrics.length
                  ? `${fmt(run.total_duration_sec, 1)} s`
                  : "Not measured"}
              </strong>
            </div>
          </div>
          {runInProgress && (
            <div className="training-time-estimate" role="status">
              <strong>
                Estimated training time remaining:{" "}
                {executionStatus === "QUEUED"
                  ? "Waiting in queue"
                  : timeEstimate && timeEstimate.remainingEpochs > 0
                    ? `about ${formatDuration(timeEstimate.remainingSeconds)}`
                    : timeEstimate
                      ? "Finishing run"
                      : "Estimating…"}
              </strong>
              <p>
                {timeEstimate && timeEstimate.remainingEpochs > 0
                  ? `${timeEstimate.completed} completed epoch(s): ${fmt(timeEstimate.measuredSeconds, 1)} s measured ÷ ${timeEstimate.completed} = ${fmt(timeEstimate.meanSeconds, 1)} s/epoch × ${timeEstimate.remainingEpochs} remaining epoch(s). Updated at epoch completion; time since that point is not subtracted.`
                  : "Timing becomes available after the first full training and validation epoch is recorded."}{" "}
                Queue wait, dataset/weight downloads, checkpoint saving, and
                finalization are excluded. Future epoch durations may vary.
              </p>
            </div>
          )}
          <div
            className="visually-hidden"
            aria-live="polite"
            aria-atomic="true"
          >
            Run {run.id}: {executionStatus}; {metrics.length} of {run.epochs}{" "}
            epochs recorded.
          </div>
          {runInProgress && (
            <section
              className="execution-stage"
              aria-live="polite"
              aria-atomic="true"
            >
              <div className="execution-pipeline" aria-label="Execution stages">
                {pipelineSteps.map((step, index) => (
                  <div
                    key={step.key}
                    className={`execution-step is-${step.state}`}
                  >
                    <span className="execution-step-node" aria-hidden="true">
                      {step.state === "done" ? "✓" : index + 1}
                    </span>
                    <span className="execution-step-label">{step.label}</span>
                  </div>
                ))}
              </div>
              <div className="execution-stage-heading">
                <span
                  className="execution-stage-dot is-pulsing"
                  aria-hidden="true"
                />
                <div>
                  <strong>
                    {isPreparingDataset
                      ? `Preparing ${stageProgress?.dataset || run.dataset?.name || preparationName || run.config?.dataset_name || "dataset"}`
                      : stageProgress?.phase === "validation"
                        ? `Validating epoch ${stageProgress.epoch} of ${run.epochs}`
                        : stageProgress?.phase === "training"
                          ? `Training epoch ${stageProgress.epoch} of ${run.epochs}`
                          : stageProgress?.message ||
                            (executionStatus === "QUEUED"
                              ? "Waiting for the training worker"
                              : "Starting training pipeline")}
                  </strong>
                  <p>
                    {isPreparingDataset
                      ? `${downloadPercent === 100 ? "Download complete; verifying and extracting. " : downloadPercent !== null ? `Archive download ${downloadPercent}% · ` : ""}${stageProgress?.downloaded_bytes ? `${(stageProgress.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB received · ` : ""}Dataset preparation happens before epoch 1.`
                      : stageProgress?.phase === "training"
                        ? `Batch ${stageProgress.batch_idx} of ${stageProgress.total_batches} · learning rate ${stageProgress.lr} · batch accuracy ${fmt(stageProgress.running_acc)}%`
                        : stageProgress?.phase === "validation"
                          ? "Measuring validation loss and accuracy before saving this epoch."
                          : isCloudRun
                            ? "Kaggle buffers stdout during batch execution; live epochs and artifacts sync automatically when the kernel finishes."
                            : metrics.length
                              ? `${metrics.length} of ${run.epochs} epochs saved.`
                              : "The run is starting; the first epoch metric appears after training and validation complete."}
                  </p>
                </div>
                <div className="execution-stage-meta">
                  <span className="execution-stage-timer">
                    {formatElapsed(elapsedSeconds)} elapsed
                  </span>
                  <span className="execution-stage-count">
                    {metrics.length}/{run.epochs} epochs
                  </span>
                </div>
              </div>
              {isPreparingDataset && downloadPercent !== null ? (
                <progress
                  aria-label="Dataset archive download"
                  value={downloadPercent}
                  max="100"
                />
              ) : isWaitingIndeterminate ? (
                <div
                  className="execution-stage-track is-indeterminate"
                  role="progressbar"
                  aria-label="Execution in progress"
                  aria-valuetext="Running pipeline stage"
                >
                  <span />
                </div>
              ) : stageProgress?.phase === "training" &&
                stageProgress.total_batches ? (
                <label className="execution-progress-label">
                  <span>
                    Overall training progress (includes current epoch batches)
                  </span>
                  <progress
                    aria-label="Overall training progress including current epoch batches"
                    value={
                      (stageProgress.epoch - 1) * stageProgress.total_batches +
                      stageProgress.batch_idx
                    }
                    max={run.epochs * stageProgress.total_batches}
                  />
                </label>
              ) : (
                <label className="execution-progress-label">
                  <span>Completed epochs (saved after validation)</span>
                  <progress
                    aria-label="Completed epochs"
                    value={metrics.length}
                    max={run.epochs}
                  />
                </label>
              )}
              {Number(run.epochs) > 0 && (
                <div
                  className="execution-epoch-pills"
                  aria-label="Epoch status"
                >
                  {Array.from({ length: Number(run.epochs) }, (_, idx) => {
                    const epochNum = idx + 1;
                    const recorded = metrics.find(
                      (m) => Number(m.epoch) === epochNum,
                    );
                    const isCurrent =
                      !recorded &&
                      Number(stageProgress?.epoch) === epochNum &&
                      (phase === "training" || phase === "validation");
                    return (
                      <span
                        key={epochNum}
                        className={`execution-epoch-pill ${recorded ? "is-done" : isCurrent ? "is-active" : "is-pending"}`}
                      >
                        E{epochNum}
                        {recorded ? ` · ${fmt(recorded.val_acc, 1)}%` : ""}
                      </span>
                    );
                  })}
                </div>
              )}
            </section>
          )}
          <LiveMetricsDashboard
            run={run}
            runInProgress={runInProgress}
            liveSamples={liveSamples}
            metrics={metrics}
          />
          {run.error && <pre className="error">{run.error}</pre>}
          {liveError && (
            <p className="error" role="status">
              Live updates paused temporarily: {liveError}. Retrying…
            </p>
          )}
          <NotebookGuide runId={run.id} />
          {imageArtifacts.length > 0 && (
            <details className="run-disclosure">
              <summary>Run visuals ({imageArtifacts.length})</summary>
              <div className="run-image-grid">
                {imageArtifacts.map((artifact) => (
                  <figure className="evaluation-image-card" key={artifact.id}>
                    <figcaption>
                      {artifact.kind === "dataset_preview_png"
                        ? "Training dataset preview"
                        : artifact.kind === "training_curves_png"
                          ? "Cloud training curves"
                          : artifact.kind === "confusion_matrix_png"
                            ? "Final test confusion matrix"
                            : artifact.kind.replaceAll("_", " ")}
                    </figcaption>
                    <a
                      href={`/api/v1/runs/artifacts/${artifact.id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <img
                        src={`/api/v1/runs/artifacts/${artifact.id}`}
                        alt={artifact.kind.replaceAll("_", " ")}
                      />
                    </a>
                  </figure>
                ))}
              </div>
            </details>
          )}
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
                    <th key={h} scope="col">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const bestVal = metrics.reduce(
                    (best, row) =>
                      row.val_acc != null && Number(row.val_acc) > best
                        ? Number(row.val_acc)
                        : best,
                    -1,
                  );
                  return metrics.map((m, idx) => {
                    const prevVal = idx > 0 ? metrics[idx - 1]?.val_acc : null;
                    const delta =
                      prevVal != null && m.val_acc != null
                        ? Number(m.val_acc) - Number(prevVal)
                        : null;
                    const isBest =
                      m.val_acc != null &&
                      Number(m.val_acc) === bestVal &&
                      bestVal >= 0;
                    return (
                      <tr
                        key={m.id}
                        className={isBest ? "epoch-row-best" : undefined}
                      >
                        <td>
                          {m.epoch}
                          {isBest && (
                            <span className="epoch-best-badge">Best</span>
                          )}
                        </td>
                        <td>{fmt(m.train_loss, 4)}</td>
                        <td>{fmt(m.train_acc)}</td>
                        <td>{fmt(m.val_loss, 4)}</td>
                        <td>
                          <div className="epoch-acc-cell">
                            <span>{fmt(m.val_acc)}</span>
                            {delta !== null && (
                              <small
                                className={delta >= 0 ? "is-up" : "is-down"}
                              >
                                {delta >= 0 ? "+" : ""}
                                {delta.toFixed(2)}%
                              </small>
                            )}
                            <div className="epoch-acc-bar" aria-hidden="true">
                              <span
                                style={{
                                  width: `${Math.min(100, Math.max(0, Number(m.val_acc) || 0))}%`,
                                }}
                              />
                            </div>
                          </div>
                        </td>
                        <td>{m.learning_rate ?? "Unknown"}</td>
                        <td>{fmt(m.epoch_time_sec, 1)}</td>
                      </tr>
                    );
                  });
                })()}
                {!metrics.length && (
                  <tr>
                    <td colSpan="7">
                      No epoch metrics saved yet. Values appear after the first
                      training and validation epoch finishes.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <details>
            <summary>
              Execution log (preparation, completion, warnings and errors)
            </summary>
            <div className="events">
              {events.some(
                (e) =>
                  !/^Epoch \d+\/\d+: train .*validation .*loss /.test(
                    e.message,
                  ),
              )
                ? events
                    .filter(
                      (e) =>
                        !/^Epoch \d+\/\d+: train .*validation .*loss /.test(
                          e.message,
                        ),
                    )
                    .map((e) => (
                      <p key={e.id}>
                        {formatTime(e.created_at)} · {e.message}
                      </p>
                    ))
                : "No operational messages recorded. Epoch results are shown in the metrics table above."}
            </div>
          </details>
          <Json
            data={{
              configuration: run.config,
              dataset: run.dataset,
              environment: run.environment,
              tracking: run.tracking,
            }}
            label="Configuration, provenance, and external tracking status"
          />
          <details className="run-disclosure">
            <summary>Artifacts ({run.artifacts.length})</summary>
            {run.artifacts.length ? (
              <ul className="artifact-list">
                {run.artifacts.map((a) => (
                  <li key={a.id}>
                    <a href={`/api/v1/runs/artifacts/${a.id}`}>
                      {a.kind.replaceAll("_", " ")}
                    </a>
                    <span>{(a.size_bytes / 1024).toFixed(1)} KB</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No catalogued artifacts. Legacy files were preserved.</p>
            )}
          </details>
        </>
      )}
    </Panel>
  );
}
