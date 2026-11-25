import React, { useState, useCallback, useRef } from "react";

const numeric = (value) =>
  value !== null &&
  value !== undefined &&
  value !== "" &&
  Number.isFinite(Number(value));
const observedTime = (value) =>
  typeof value === "number" ? value : Date.parse(value || "") || 0;

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
  headerActions = null,
  onExpand = null,
}) {
  const [tooltip, setTooltip] = useState(null);
  const svgRef = useRef(null);
  const recorded = samples
    .map((sample, index) => ({ sample, index, value: sample[field] }))
    .filter(({ value }) => numeric(value));
  if (!recorded.length)
    return (
      <div className="live-chart-empty">
        {title} has no recorded{" "}
        {source === "epoch" ? "epoch values" : "batch samples"} for this run.
      </div>
    );
  const values = recorded.map(({ value }) => Number(value));
  const useLog = logScale && values.every((value) => value > 0);
  const smoothWindow = Math.max(1, Number(smoothing) || 1);
  const plotted = values.map((_, index) => {
    const recent = values.slice(
      Math.max(0, index - smoothWindow + 1),
      index + 1,
    );
    const average =
      recent.reduce((sum, value) => sum + value, 0) / recent.length;
    return useLog ? Math.log10(average) : average;
  });
  const accuracy = field.endsWith("acc") || field.includes("accuracy");
  const min = Math.min(...plotted);
  const max = Math.max(...plotted);
  const spread = Math.max(0.02, (max - min) * 0.12);
  const low = useLog ? min - spread : accuracy ? 0 : Math.max(0, min - spread);
  const high = useLog ? max + spread : accuracy ? 100 : max + spread;
  const step = (point) =>
    source === "epoch"
      ? Number(point.epoch)
      : point.total_batches
        ? (Number(point.epoch) - 1) * Number(point.total_batches) +
          Number(point.batch_idx)
        : Number(point.epoch);
  const xValue = ({ sample, index }) =>
    source === "epoch"
      ? step(sample)
      : xAxis === "time"
        ? observedTime(sample.observed_at)
        : xAxis === "sample"
          ? index
          : step(sample);
  const firstX = xValue(recorded[0]);
  const lastX = xValue(recorded.at(-1));
  const x = (point) =>
    52 + ((xValue(point) - firstX) / Math.max(1, lastX - firstX)) * 590;
  const y = (value) => 170 - ((value - low) / Math.max(1e-9, high - low)) * 135;
  const segments = [];
  let current = [];
  recorded.forEach((point, index) => {
    if (index && point.index !== recorded[index - 1].index + 1) {
      if (current.length) segments.push(current);
      current = [];
    }
    current.push([x(point), y(plotted[index])]);
  });
  if (current.length) segments.push(current);
  const tick = (value) =>
    (useLog ? 10 ** value : value).toFixed(accuracy ? 0 : 2);
  const axisName =
    source === "epoch"
      ? "Epoch"
      : xAxis === "time"
        ? "Observation"
        : xAxis === "sample"
          ? "Sample"
          : "Step";
  const latest = values.at(-1);

  const handleMouseMove = useCallback(
    (e) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      // Map mouse X to SVG coordinate space (viewBox 0 0 680 210)
      const svgX = ((e.clientX - rect.left) / rect.width) * 680;
      // Find the closest recorded data point by x position
      let best = null;
      let bestDist = Infinity;
      recorded.forEach((point, index) => {
        const px = x(point);
        const dist = Math.abs(px - svgX);
        if (dist < bestDist) {
          bestDist = dist;
          best = { point, index };
        }
      });
      if (!best || bestDist > 24) {
        setTooltip(null);
        return;
      }
      const { point, index } = best;
      const rawValue = Number(point.value);
      const displayValue = useLog ? 10 ** plotted[index] : plotted[index];
      const label =
        source === "epoch"
          ? `Epoch ${point.sample.epoch}`
          : `Step ${point.sample.batch_idx ?? point.index + 1}`;
      setTooltip({
        cx: x(point),
        cy: y(plotted[index]),
        label,
        value: rawValue.toFixed(accuracy ? 2 : 4) + unit,
        smoothed:
          smoothWindow > 1
            ? displayValue.toFixed(accuracy ? 2 : 4) + unit
            : null,
      });
    },
    [
      recorded,
      plotted,
      x,
      y,
      source,
      xAxis,
      unit,
      accuracy,
      useLog,
      smoothWindow,
    ],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  return (
    <figure className="live-training-chart">
      <figcaption className="live-training-chart-header">
        <div className="live-chart-title-group">
          {headerActions}
          <span className="live-chart-title">{title}</span>
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
      <svg
        ref={svgRef}
        viewBox="0 0 680 210"
        role="img"
        style={{ cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        aria-label={`${title}: ${recorded.length} recorded ${source === "epoch" ? "epochs" : "batch samples"}; latest ${latest.toFixed(2)}${unit}; ${useLog ? "logarithmic" : "linear"} scale. ${segments.length > 1 ? "Gaps indicate missing samples." : ""}`}
      >
        {/* Y-axis baseline */}
        <line
          x1="52"
          x2="52"
          y1="35"
          y2="170"
          stroke="var(--chart-grid, #354154)"
          strokeOpacity="0.6"
        />
        {/* X-axis baseline */}
        <line
          x1="52"
          x2="642"
          y1="170"
          y2="170"
          stroke="var(--chart-grid, #354154)"
          strokeOpacity="0.6"
        />
        {[0, 0.5, 1].map((position) => (
          <g key={position}>
            <line
              x1="52"
              x2="642"
              y1={35 + 135 * position}
              y2={35 + 135 * position}
              stroke="var(--chart-grid, #354154)"
              strokeOpacity={position === 1 ? 0 : 0.5}
              strokeDasharray={position === 0 ? undefined : "4 3"}
            />
            <text
              className="chart-axis-label"
              x="48"
              y={39 + 135 * position}
              textAnchor="end"
            >
              {tick(high - (high - low) * position)}
            </text>
          </g>
        ))}
        {segments.map((segment, index) =>
          segment.length > 1 ? (
            <polyline
              key={index}
              fill="none"
              stroke={color}
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
              points={segment.map(([px, py]) => `${px},${py}`).join(" ")}
            />
          ) : (
            <circle
              key={index}
              cx={segment[0][0]}
              cy={segment[0][1]}
              r="4"
              fill={color}
            />
          ),
        )}
        {/* Visible data point dots */}
        {recorded.map((point, index) => (
          <circle
            key={`dot-${point.index}`}
            cx={x(point)}
            cy={y(plotted[index])}
            r="3"
            fill={color}
            fillOpacity="0.7"
            stroke="var(--tt-surface, #161b22)"
            strokeWidth="1.5"
          />
        ))}
        {/* Hover crosshair + highlighted dot */}
        {tooltip && (
          <g>
            <line
              x1={tooltip.cx}
              x2={tooltip.cx}
              y1="35"
              y2="170"
              stroke={color}
              strokeOpacity="0.4"
              strokeDasharray="3 3"
            />
            <circle
              cx={tooltip.cx}
              cy={tooltip.cy}
              r="5.5"
              fill={color}
              stroke="var(--tt-surface, #161b22)"
              strokeWidth="2"
            />
          </g>
        )}
        <text className="chart-axis-label" x="52" y="198">
          {axisName}{" "}
          {source === "epoch" || xAxis === "step"
            ? Math.round(firstX)
            : "start"}
        </text>
        <text className="chart-axis-label" x="560" y="198">
          {axisName}{" "}
          {source === "epoch" || xAxis === "step"
            ? Math.round(lastX)
            : "latest"}
        </text>
      </svg>
      {/* Tooltip bubble — rendered as HTML overlay so it can overflow the SVG */}
      {tooltip && (
        <div
          className="live-chart-tooltip"
          style={{
            left: `${((tooltip.cx - 52) / 590) * 100}%`,
          }}
        >
          <span className="live-chart-tooltip-label">{tooltip.label}</span>
          <span className="live-chart-tooltip-value">{tooltip.value}</span>
          {tooltip.smoothed && (
            <span className="live-chart-tooltip-smoothed">
              smoothed {tooltip.smoothed}
            </span>
          )}
        </div>
      )}
      <small>
        {source === "batch"
          ? "Saved batch samples; see chart CSV for exact observation times."
          : "Saved after each completed validation epoch."}
        {smoothWindow > 1
          ? ` Display-only ${smoothWindow}-sample moving average.`
          : ""}
        {logScale && !useLog
          ? " Log scale unavailable because this metric includes zero or negative values; linear scale shown."
          : ""}
      </small>
    </figure>
  );
}
