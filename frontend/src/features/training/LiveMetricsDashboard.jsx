import React from "react";
import useLiveChartSettings from "./useLiveChartSettings";
import { fmt } from "../../components/Common";
import LiveChartControls from "./LiveChartControls";
import LiveChartGrid from "./LiveChartGrid";
import TrainingTrajectory3D from "../../components/TrainingTrajectory3D";

function KpiSparkline({ values, color }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1e-6, max - min);
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 72;
      const y = 20 - ((v - min) / span) * 16;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg
      className="kpi-sparkline"
      viewBox="0 0 72 24"
      aria-hidden="true"
      focusable="false"
    >
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export default function LiveMetricsDashboard({
  run,
  runInProgress,
  liveSamples,
  metrics,
}) {
  const settings = useLiveChartSettings({ run, liveSamples, metrics });
  const latestLiveSample = liveSamples.at(-1);
  const latestEpoch = metrics.at(-1);
  const firstEpoch = metrics[0];

  const lossSeries = liveSamples.length
    ? liveSamples.map((s) => Number(s.batch_loss)).filter(Number.isFinite)
    : metrics.map((m) => Number(m.train_loss)).filter(Number.isFinite);
  const accSeries = liveSamples.length
    ? liveSamples.map((s) => Number(s.running_acc)).filter(Number.isFinite)
    : metrics.map((m) => Number(m.val_acc)).filter(Number.isFinite);
  const paceSeries = liveSamples.length
    ? liveSamples.map((s) => Number(s.samples_per_sec)).filter(Number.isFinite)
    : metrics.map((m) => Number(m.epoch_time_sec)).filter(Number.isFinite);

  const avgEpochSec =
    paceSeries.length && !liveSamples.length
      ? paceSeries.reduce((a, b) => a + b, 0) / paceSeries.length
      : null;
  const lossDelta =
    !liveSamples.length &&
    firstEpoch?.train_loss > 0 &&
    latestEpoch?.train_loss != null
      ? ((latestEpoch.train_loss - firstEpoch.train_loss) /
          firstEpoch.train_loss) *
        100
      : null;
  const accDelta =
    !liveSamples.length &&
    firstEpoch?.val_acc != null &&
    latestEpoch?.val_acc != null &&
    metrics.length > 1
      ? latestEpoch.val_acc - firstEpoch.val_acc
      : null;

  return (
    <>
      {(runInProgress || liveSamples.length > 0 || metrics.length > 0) && (
        <section
          className="live-training-panel"
          aria-label="Live training measurements"
        >
          <div className="live-training-heading">
            <div>
              <strong>Run metrics charts</strong>
              <span>
                {liveSamples.length > 0
                  ? "Live batch samples and saved epoch metrics"
                  : "Saved epoch metrics and validation progression"}
              </span>
            </div>
            <span className="live-sample-count">
              {liveSamples.length} batch samples · {metrics.length} epochs
            </span>
          </div>
          <div className="live-training-kpis">
            <div className="kpi-card">
              <div className="kpi-card-top">
                <small>
                  {latestLiveSample?.batch_loss != null
                    ? "Latest batch loss"
                    : "Final train loss"}
                </small>
                <KpiSparkline values={lossSeries} color="#2272b4" />
              </div>
              <div className="kpi-card-value">
                <strong>
                  {latestLiveSample?.batch_loss != null
                    ? fmt(latestLiveSample.batch_loss, 3)
                    : latestEpoch?.train_loss != null
                      ? fmt(latestEpoch.train_loss, 4)
                      : "--"}
                </strong>
                {lossDelta !== null && (
                  <span className="kpi-delta is-positive">
                    {lossDelta.toFixed(0)}% vs E1
                  </span>
                )}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-card-top">
                <small>
                  {latestLiveSample?.running_acc != null
                    ? "Running train accuracy"
                    : "Best validation accuracy"}
                </small>
                <KpiSparkline values={accSeries} color="#308613" />
              </div>
              <div className="kpi-card-value">
                <strong>
                  {latestLiveSample?.running_acc != null
                    ? `${fmt(latestLiveSample.running_acc)}%`
                    : run?.best_val_accuracy != null
                      ? `${fmt(run.best_val_accuracy)}%`
                      : latestEpoch?.val_acc != null
                        ? `${fmt(latestEpoch.val_acc)}%`
                        : "--"}
                </strong>
                {accDelta !== null && (
                  <span
                    className={`kpi-delta ${accDelta >= 0 ? "is-positive" : "is-negative"}`}
                  >
                    {accDelta >= 0 ? "+" : ""}
                    {accDelta.toFixed(2)}% vs E1
                  </span>
                )}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-card-top">
                <small>
                  {latestLiveSample?.samples_per_sec != null
                    ? "Average throughput"
                    : "Average epoch pace"}
                </small>
                <KpiSparkline values={paceSeries} color="#9a641d" />
              </div>
              <div className="kpi-card-value">
                <strong>
                  {latestLiveSample?.samples_per_sec != null
                    ? `${fmt(latestLiveSample.samples_per_sec, 1)} images/s`
                    : avgEpochSec != null
                      ? `${fmt(avgEpochSec, 1)} s/epoch`
                      : "--"}
                </strong>
                {latestEpoch?.val_loss != null && !liveSamples.length && (
                  <span className="kpi-sub">
                    Val loss {fmt(latestEpoch.val_loss, 4)}
                  </span>
                )}
              </div>
            </div>
          </div>
          <LiveChartControls
            settings={settings}
            liveSamples={liveSamples}
            metrics={metrics}
            runInProgress={runInProgress}
          />
          <LiveChartGrid
            settings={settings}
            metrics={metrics}
            runInProgress={runInProgress}
          />
          <TrainingTrajectory3D metrics={metrics} liveSamples={liveSamples} />
        </section>
      )}
    </>
  );
}
