import React, { useEffect, useRef } from "react";
import Chart from "chart.js/auto";
import InfoTooltip from "./InfoTooltip";

const numeric = (value) =>
  value !== null &&
  value !== undefined &&
  value !== "" &&
  Number.isFinite(Number(value));

export default function LiveTrainingChart({
  samples = [],
  field,
  title,
  color,
  unit = "",
  xAxis = "step",
  smoothing = 1,
  logScale = false,
  source = "batch",
  compareField = null,
  compareLabel = null,
  compareColor = "#f59e0b",
  headerActions = null,
  onExpand = null,
}) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  const recorded = samples
    .map((sample, index) => ({ sample, index, value: sample[field] }))
    .filter(({ value }) => numeric(value));

  const values = recorded.map(({ value }) => Number(value));
  const compareValues = compareField
    ? recorded.map(({ sample }) =>
        numeric(sample[compareField]) ? Number(sample[compareField]) : null,
      )
    : [];

  const smoothWindow = Math.max(1, Number(smoothing) || 1);
  const smoothSeries = (arr) =>
    arr.map((val, index) => {
      if (val === null) return null;
      const recent = arr
        .slice(Math.max(0, index - smoothWindow + 1), index + 1)
        .filter((v) => v !== null);
      if (!recent.length) return null;
      return recent.reduce((sum, v) => sum + v, 0) / recent.length;
    });

  const plotted = smoothSeries(values);
  const comparePlotted = smoothSeries(compareValues);
  const accuracy = field.endsWith("acc") || field.includes("accuracy");
  const allNumeric = [...plotted, ...comparePlotted].filter(
    (v) => v !== null && Number.isFinite(v),
  );
  const useLog =
    logScale && allNumeric.length > 0 && allNumeric.every((v) => v > 0);
  const latest = values.at(-1);

  const labels = recorded.map(({ sample, index }) => {
    if (source === "epoch") return `Epoch ${sample.epoch}`;
    if (xAxis === "time" && sample.observed_at) {
      const d = new Date(sample.observed_at);
      return Number.isNaN(d.getTime())
        ? `Sample ${index + 1}`
        : d.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
    }
    if (xAxis === "sample") return `#${index + 1}`;
    return sample.total_batches
      ? `E${sample.epoch}·${sample.batch_idx}`
      : `Step ${sample.batch_idx ?? index + 1}`;
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !recorded.length) return undefined;

    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }

    const ctx = canvas.getContext("2d");
    const isDark = Boolean(
      document.querySelector(".app-shell")?.classList.contains("theme-dark"),
    );
    const gridColor = isDark
      ? "rgba(148, 163, 184, 0.14)"
      : "rgba(15, 23, 42, 0.08)";
    const tickColor = isDark ? "#8b949e" : "#57606a";
    const tooltipBg = isDark ? "#0d1117" : "#ffffff";
    const tooltipBorder = isDark ? "#30363d" : "#d0d7de";
    const tooltipText = isDark ? "#e6edf3" : "#1f2328";

    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height || 220);
    gradient.addColorStop(0, `${color}40`);
    gradient.addColorStop(1, `${color}02`);

    const minVal = Math.min(...allNumeric);
    const maxVal = Math.max(...allNumeric);
    const pad = Math.max(accuracy ? 0.5 : 0.02, (maxVal - minVal) * 0.14);

    const datasets = [
      {
        label: title,
        data: plotted,
        borderColor: color,
        backgroundColor: gradient,
        fill: true,
        borderWidth: 2.4,
        tension: 0.32,
        pointRadius: recorded.length <= 20 ? 3.5 : 0,
        pointHoverRadius: 5.5,
        pointBackgroundColor: color,
      },
    ];

    if (compareField && comparePlotted.some((v) => v !== null)) {
      datasets.push({
        label: compareLabel || compareField,
        data: comparePlotted,
        borderColor: compareColor,
        backgroundColor: "transparent",
        fill: false,
        borderWidth: 2,
        borderDash: [5, 4],
        tension: 0.32,
        pointRadius: recorded.length <= 20 ? 3 : 0,
        pointHoverRadius: 5,
        pointBackgroundColor: compareColor,
      });
    }

    chartRef.current = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 280 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: "bottom",
            labels: {
              color: tickColor,
              boxWidth: 14,
              boxHeight: 3,
              font: { size: 11 },
            },
          },
          tooltip: {
            backgroundColor: tooltipBg,
            borderColor: tooltipBorder,
            borderWidth: 1,
            titleColor: tooltipText,
            bodyColor: tooltipText,
            padding: 9,
            callbacks: {
              label: (item) => {
                const v = item.parsed.y;
                if (v == null) return "";
                return `${item.dataset.label}: ${v.toFixed(accuracy ? 2 : 4)}${unit}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: tickColor,
              maxTicksLimit: 7,
              font: { size: 11 },
            },
          },
          y: {
            type: useLog ? "logarithmic" : "linear",
            min: useLog ? undefined : Math.max(0, minVal - pad),
            max: useLog
              ? undefined
              : accuracy
                ? Math.min(100, maxVal + pad)
                : maxVal + pad,
            grid: { color: gridColor },
            ticks: {
              color: tickColor,
              maxTicksLimit: 5,
              font: { size: 11 },
              callback: (val) => Number(val).toFixed(accuracy ? 1 : 2),
            },
          },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [
    JSON.stringify(labels),
    JSON.stringify(plotted),
    JSON.stringify(comparePlotted),
    color,
    compareColor,
    title,
    compareLabel,
    unit,
    accuracy,
    useLog,
  ]);

  if (!recorded.length) {
    return (
      <div className="live-chart-empty">
        {title} has no recorded{" "}
        {source === "epoch" ? "epoch values" : "batch samples"} for this run.
      </div>
    );
  }

  return (
    <figure className="live-training-chart">
      <figcaption className="live-training-chart-header">
        <div className="live-chart-title-group">
          {headerActions}
          <span className="live-chart-title">{title}</span>
          <InfoTooltip label={`About ${title}`}>
            {compareLabel
              ? `Compares ${title} (solid) against ${compareLabel} (dashed) across ${source === "epoch" ? "completed epochs" : "training steps"}. Hover to inspect exact values.`
              : source === "epoch"
                ? `Tracks ${title} recorded after each completed validation epoch. Hover any point to inspect exact values.`
                : `Tracks ${title} from recorded training batch samples. Hover to inspect exact values.`}
          </InfoTooltip>
        </div>
        <div className="live-chart-meta-group">
          <strong className="live-chart-value">
            {latest.toFixed(2)}
            {unit}
          </strong>
          {onExpand && (
            <button
              type="button"
              className="link live-chart-expand-btn"
              onClick={onExpand}
              aria-label={`Expand ${title} chart`}
            >
              Expand ↗
            </button>
          )}
        </div>
      </figcaption>
      <div className="live-chart-canvas-wrap">
        <canvas ref={canvasRef} aria-label={`${title} chart`} />
      </div>
      {logScale && !useLog && (
        <small>
          Log scale unavailable because this metric includes zero or negative
          values; linear scale shown.
        </small>
      )}
    </figure>
  );
}
