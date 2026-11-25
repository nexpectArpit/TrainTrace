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
  const isPreparingDataset =
    runInProgress &&
    metrics.length === 0 &&
    (live?.progress?.phase === "dataset_preparation" ||
      (!live?.progress && Boolean(latestPreparationEvent)));
  const stageProgress = live?.progress;
  const imageArtifacts =
    run?.artifacts?.filter((artifact) =>
      [
        "dataset_preview_png",
        "training_curves_png",
        "confusion_matrix_png",
      ].includes(artifact.kind),
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
  const eventTimestamp = latestPreparationEvent?.created_at;
  const eventStartedAt = eventTimestamp
    ? Date.parse(
        eventTimestamp.includes("T")
          ? eventTimestamp
          : `${eventTimestamp.replace(" ", "T")}Z`,
      ) / 1000
    : Number.NaN;
  const elapsedSeconds = isPreparingDataset
    ? Math.max(
        0,
        Math.floor(
          Date.now() / 1000 -
            (stageProgress?.started_at || eventStartedAt || Date.now() / 1000),
        ),
      )
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
              <div className="execution-stage-heading">
                <span
                  className={`execution-stage-dot ${isPreparingDataset ? "is-pulsing" : ""}`}
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
                      ? `${downloadPercent === 100 ? "Download complete; verifying and extracting. " : downloadPercent !== null ? `Archive download ${downloadPercent}% · ` : ""}${stageProgress?.downloaded_bytes ? `${(stageProgress.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB received · ` : ""}Dataset preparation happens before epoch 1. ${elapsedSeconds ? `${formatElapsed(elapsedSeconds)} elapsed.` : ""}`
                      : stageProgress?.phase === "training"
                        ? `Batch ${stageProgress.batch_idx} of ${stageProgress.total_batches} · learning rate ${stageProgress.lr} · batch accuracy ${fmt(stageProgress.running_acc)}%`
                        : stageProgress?.phase === "validation"
                          ? "Measuring validation loss and accuracy before saving this epoch."
                          : metrics.length
                            ? `${metrics.length} of ${run.epochs} epochs saved.`
                            : "The run is starting; the first epoch metric appears after training and validation complete."}
                  </p>
                </div>
                <span className="execution-stage-count">
                  {metrics.length}/{run.epochs} epochs
                </span>
              </div>
              {isPreparingDataset && downloadPercent !== null ? (
                <progress
                  aria-label="Dataset archive download"
                  value={downloadPercent}
                  max="100"
                />
              ) : isPreparingDataset ? (
                <div
                  className="execution-stage-track is-indeterminate"
                  role="progressbar"
                  aria-label="Preparing dataset"
                  aria-valuetext="Downloading or extracting dataset"
                >
                  <span />
                </div>
              ) : stageProgress?.phase === "training" &&
                stageProgress.total_batches ? (
                <label className="execution-progress-label">
                  <span>
                    Overall training progress — includes current epoch batches
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
                  <span>Completed epochs — saved after validation</span>
                  <progress
                    aria-label="Completed epochs"
                    value={metrics.length}
                    max={run.epochs}
                  />
                </label>
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
            <section className="run-image-gallery" aria-label="Run visuals">
              <h3>Run visuals</h3>
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
            </section>
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
              Execution log — preparation, completion, warnings and errors
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
          <h3>Artifacts</h3>
          {run.artifacts.length ? (
            <ul>
              {run.artifacts.map((a) => (
                <li key={a.id}>
                  <a href={`/api/v1/runs/artifacts/${a.id}`}>{a.kind}</a> ·{" "}
                  {(a.size_bytes / 1024).toFixed(1)} KB
                </li>
              ))}
            </ul>
          ) : (
            <p>No catalogued artifacts. Legacy files were preserved.</p>
          )}
        </>
      )}
    </Panel>
  );
}
