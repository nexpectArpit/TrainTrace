import React from "react";
import { Field, Select } from "../../components/Common";
import { liveChartDefinitions } from "./chartDefinitions";

export default function LiveChartControls({
  settings,
  liveSamples,
  metrics,
  runInProgress,
}) {
  const {
    chartSearch,
    setChartSearch,
    chartAxis,
    setChartAxis,
    smoothing,
    setSmoothing,
    logScale,
    setLogScale,
    chartPaused,
    setChartPaused,
    setPausedSamples,
    chartSamples,
    downloadChartData,
    chartOrder,
    setChartOrder,
    hiddenCharts,
    setHiddenCharts,
    newChartField,
    setNewChartField,
    hasRecordedMetric,
  } = settings;
  const availableVisibilityCharts = chartOrder
    .map((field) => liveChartDefinitions.find((chart) => chart.field === field))
    .filter((chart) => chart && (hasRecordedMetric(chart) || runInProgress));
  const addableCharts = liveChartDefinitions.filter(
    (chart) => !chartOrder.includes(chart.field) && hasRecordedMetric(chart),
  );
  return (
    <>
      <div className="live-chart-toolbar">
        <Field
          label="Find a chart"
          type="search"
          value={chartSearch}
          onChange={setChartSearch}
          placeholder="Loss, accuracy, throughput"
        />
        <Select
          label="Horizontal axis"
          value={chartAxis}
          onChange={setChartAxis}
        >
          <option value="step">Training step</option>
          <option value="time">Observation time</option>
          <option value="sample">Observed samples</option>
        </Select>
        <Select
          label="Smoothing"
          value={String(smoothing)}
          onChange={(value) => setSmoothing(Number(value))}
        >
          <option value="1">None</option>
          <option value="5">5 samples</option>
          <option value="15">15 samples</option>
        </Select>
        <div className="live-chart-toolbar-actions">
          <label className="live-chart-check">
            <input
              type="checkbox"
              checked={logScale}
              onChange={(event) => setLogScale(event.target.checked)}
            />{" "}
            Log scale
          </label>
          {runInProgress && (
            <button
              type="button"
              onClick={() => {
                setPausedSamples(liveSamples);
                setChartPaused(!chartPaused);
              }}
            >
              {chartPaused ? "Resume charts" : "Pause charts"}
            </button>
          )}
          <button
            type="button"
            disabled={!chartSamples.length && !metrics.length}
            onClick={downloadChartData}
          >
            Download chart CSV
          </button>
        </div>
      </div>
      {availableVisibilityCharts.length > 0 && (
        <div className="live-chart-visibility" aria-label="Visible charts">
          {availableVisibilityCharts.map((chart) => (
            <label key={chart.field}>
              <input
                type="checkbox"
                checked={!hiddenCharts.includes(chart.field)}
                onChange={() =>
                  setHiddenCharts((current) =>
                    current.includes(chart.field)
                      ? current.filter((item) => item !== chart.field)
                      : [...current, chart.field],
                  )
                }
              />{" "}
              {chart.title}
            </label>
          ))}
        </div>
      )}
      {addableCharts.length > 0 && (
        <div className="live-chart-builder">
          <div className="live-chart-builder-controls">
            <Select
              label="Add a metric chart"
              value={newChartField}
              onChange={setNewChartField}
            >
              <option value="">Choose a recorded metric</option>
              {addableCharts.map((chart) => (
                <option key={chart.field} value={chart.field}>
                  {chart.title} · {chart.source}
                </option>
              ))}
            </Select>
            <button
              type="button"
              className="add-chart-btn"
              disabled={!newChartField}
              onClick={() => {
                setChartOrder((current) => [...current, newChartField]);
                setHiddenCharts((current) =>
                  current.filter((field) => field !== newChartField),
                );
                setNewChartField("");
              }}
            >
              Add chart
            </button>
          </div>
        </div>
      )}
    </>
  );
}
