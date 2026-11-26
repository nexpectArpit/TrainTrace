import React from "react";
import LiveTrainingChart from "../../components/LiveTrainingChart";
import { liveChartDefinitions } from "./chartDefinitions";

export default function LiveChartGrid({ settings, metrics, runInProgress }) {
  const {
    chartOrder,
    setChartOrder,
    hiddenCharts,
    chartSearch,
    hasRecordedMetric,
    chartSamples,
    chartAxis,
    smoothing,
    logScale,
    chartType,
    moveChart,
    placeChart,
    expandedChart,
    setExpandedChart,
  } = settings;
  return (
    <>
      <div className="live-training-charts">
        {chartOrder
          .map((field) =>
            liveChartDefinitions.find((chart) => chart.field === field),
          )
          .filter(
            (chart) =>
              chart &&
              !hiddenCharts.includes(chart.field) &&
              chart.title.toLowerCase().includes(chartSearch.toLowerCase()) &&
              (hasRecordedMetric(chart) ||
                (runInProgress && chart.field !== "device_memory_mb")),
          )
          .map((chart) => (
            <div
              className="live-chart-card"
              key={chart.field}
              draggable
              onDragStart={(event) =>
                event.dataTransfer.setData("text/plain", chart.field)
              }
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                placeChart(
                  event.dataTransfer.getData("text/plain"),
                  chart.field,
                );
              }}
            >
              <LiveTrainingChart
                samples={chart.source === "epoch" ? metrics : chartSamples}
                xAxis={chartAxis}
                smoothing={smoothing}
                logScale={logScale}
                chartType={chartType}
                onExpand={() => setExpandedChart(chart)}
                {...chart}
              />
            </div>
          ))}
      </div>
      {expandedChart && (
        <div
          className="live-chart-modal"
          role="dialog"
          aria-modal="true"
          aria-label={`${expandedChart.title} expanded chart`}
        >
          <div className="live-chart-modal-content">
            <button
              type="button"
              onClick={() => setExpandedChart(null)}
              aria-label="Close expanded chart"
            >
              ×
            </button>
            <LiveTrainingChart
              samples={
                expandedChart.source === "epoch" ? metrics : chartSamples
              }
              xAxis={chartAxis}
              smoothing={smoothing}
              logScale={logScale}
              chartType={chartType}
              {...expandedChart}
            />
          </div>
        </div>
      )}
    </>
  );
}
