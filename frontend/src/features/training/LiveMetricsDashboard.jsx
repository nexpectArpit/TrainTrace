import React from "react";
import useLiveChartSettings from "./useLiveChartSettings";
import { fmt } from "../../components/Common";
import LiveChartControls from "./LiveChartControls";
import LiveChartGrid from "./LiveChartGrid";

export default function LiveMetricsDashboard({
  run,
  runInProgress,
  liveSamples,
  metrics,
}) {
  const settings = useLiveChartSettings({ run, liveSamples, metrics });
  const latestLiveSample = liveSamples.at(-1);
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
              <span>Live batch samples and saved epoch metrics</span>
            </div>
            <span className="live-sample-count">
              {liveSamples.length} batch samples · {metrics.length} epochs
            </span>
          </div>
          <div className="live-training-kpis">
            <div>
              <small>Latest batch loss</small>
              <strong>
                {latestLiveSample?.batch_loss == null
                  ? "—"
                  : fmt(latestLiveSample.batch_loss, 3)}
              </strong>
            </div>
            <div>
              <small>Running train accuracy</small>
              <strong>
                {latestLiveSample?.running_acc == null
                  ? "—"
                  : `${fmt(latestLiveSample.running_acc)}%`}
              </strong>
            </div>
            <div>
              <small>Average throughput</small>
              <strong>
                {latestLiveSample?.samples_per_sec == null
                  ? "—"
                  : `${fmt(latestLiveSample.samples_per_sec, 1)} images/s`}
              </strong>
            </div>
          </div>
          <LiveChartControls
            settings={settings}
            liveSamples={liveSamples}
            metrics={metrics}
          />
          <LiveChartGrid
            settings={settings}
            metrics={metrics}
            runInProgress={runInProgress}
          />
        </section>
      )}
    </>
  );
}
