import React from "react";
import styles from "./MetricChart.module.css";

const colors = [
  "var(--chart-series-1)",
  "var(--chart-series-2)",
  "var(--chart-series-3)",
  "var(--chart-series-4)",
];
const patterns = [undefined, "8 5", "2 4", "12 4 2 4"];
const labels = { val_acc: "Validation accuracy", val_loss: "Validation loss" };
const units = { val_acc: "%", val_loss: "" };

function validSample(metric, field) {
  return (
    metric &&
    Number.isFinite(Number(metric.epoch)) &&
    metric[field] !== null &&
    metric[field] !== undefined &&
    Number.isFinite(Number(metric[field]))
  );
}

function segmentsFor(metrics, field) {
  const segments = [];
  let current = [];
  for (const metric of metrics) {
    if (validSample(metric, field)) current.push(metric);
    else if (current.length) {
      segments.push(current);
      current = [];
    }
  }
  if (current.length) segments.push(current);
  return segments;
}

export default function MetricChart({ runs, field, title, emptyMessage }) {
  const series = runs
    .map((run, index) => ({
      run,
      index,
      segments: segmentsFor(run.metrics || [], field),
    }))
    .filter((item) => item.segments.length);
  if (!series.length)
    return (
      <div className="empty">
        {emptyMessage ||
          (runs.length
            ? `No saved ${labels[field] || field} samples are available.`
            : "Select a run to see its metrics.")}
      </div>
    );

  const samples = series.flatMap((item) => item.segments.flat());
  const values = samples.map((metric) => Number(metric[field]));
  const maxEpoch = Math.max(
    1,
    ...samples.map((metric) => Number(metric.epoch)),
  );
  const minEpoch = Math.min(
    1,
    ...samples.map((metric) => Number(metric.epoch)),
  );
  const isAccuracy = field.endsWith("acc");
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const low = isAccuracy
    ? 0
    : Math.max(0, minValue - Math.max((maxValue - minValue) * 0.15, 0.02));
  const high = isAccuracy
    ? 100
    : maxValue + Math.max((maxValue - minValue) * 0.15, 0.02);
  const span = Math.max(high - low, 0.000001);
  const x = (epoch) =>
    60 + ((Number(epoch) - minEpoch) / Math.max(1, maxEpoch - minEpoch)) * 600;
  const y = (value) => 190 - ((Number(value) - low) / span) * 155;
  const ticks =
    maxEpoch <= 8
      ? Array.from({ length: maxEpoch }, (_, i) => i + 1)
      : [
          1,
          Math.ceil(maxEpoch / 4),
          Math.ceil(maxEpoch / 2),
          Math.ceil((maxEpoch * 3) / 4),
          maxEpoch,
        ];
  const valueLabel = (value) =>
    isAccuracy ? `${Number(value).toFixed(2)}%` : Number(value).toFixed(4);

  return (
    <figure className={`chart ${styles.chart}`}>
      <figcaption className={styles.header}>
        <span>{title}</span>
        <small>
          {series.length} {series.length === 1 ? "run" : "runs"} ·{" "}
          {samples.length} saved epoch{" "}
          {samples.length === 1 ? "sample" : "samples"}
        </small>
      </figcaption>
      <svg
        className={styles.plotSvg}
        viewBox="0 0 700 235"
        role="img"
        aria-label={`${title}. Epochs ${minEpoch} through ${maxEpoch}. Exact values are available in the epoch table.`}
      >
        {[0, 0.5, 1].map((fraction) => {
          const tickValue = high - fraction * span;
          const tickY = 35 + fraction * 155;
          return (
            <g key={fraction}>
              <line
                x1="60"
                x2="660"
                y1={tickY}
                y2={tickY}
                stroke="var(--chart-grid)"
              />
              <text
                x="53"
                y={tickY + 4}
                textAnchor="end"
                className={styles.axisText}
              >
                {isAccuracy ? tickValue.toFixed(0) : tickValue.toFixed(2)}
              </text>
            </g>
          );
        })}
        {series.map(({ run, index, segments }) => (
          <g key={run.id}>
            {segments.map(
              (segment, segmentIndex) =>
                segment.length > 1 && (
                  <polyline
                    key={segmentIndex}
                    fill="none"
                    stroke={colors[index % colors.length]}
                    strokeWidth="2.8"
                    strokeDasharray={patterns[index % patterns.length]}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={segment
                      .map((metric) => `${x(metric.epoch)},${y(metric[field])}`)
                      .join(" ")}
                  />
                ),
            )}
            {segments.flat().map((metric, pointIndex) => (
              <circle
                key={`${metric.epoch}-${pointIndex}`}
                cx={x(metric.epoch)}
                cy={y(metric[field])}
                r="4"
                fill={colors[index % colors.length]}
              >
                <title>
                  {run.approach_name}: epoch {metric.epoch},{" "}
                  {valueLabel(metric[field])}
                </title>
              </circle>
            ))}
          </g>
        ))}
        {[...new Set(ticks)].map((epoch) => (
          <g key={epoch}>
            <line
              x1={x(epoch)}
              x2={x(epoch)}
              y1="190"
              y2="195"
              stroke="var(--chart-grid)"
            />
            <text
              x={x(epoch)}
              y="215"
              textAnchor="middle"
              className={styles.axisText}
            >
              {epoch}
            </text>
          </g>
        ))}
        <text x="360" y="232" textAnchor="middle" className={styles.axisText}>
          Epoch
        </text>
      </svg>
      <div className={styles.legend} aria-label="Run legend">
        {series.map(({ run, index, segments }) => {
          const last = segments.flat().at(-1);
          return (
            <span
              key={run.id}
              className={styles.legendItem}
              title={`${run.approach_name} · ${run.id}`}
            >
              <svg
                className={styles.legendLineSvg}
                width="20"
                height="10"
                viewBox="0 0 20 10"
                aria-hidden="true"
              >
                <line
                  x1="1"
                  x2="19"
                  y1="5"
                  y2="5"
                  stroke={colors[index % colors.length]}
                  strokeWidth="2.5"
                  strokeDasharray={patterns[index % patterns.length]}
                  strokeLinecap="round"
                />
              </svg>
              <span className={styles.legendName}>{run.approach_name}</span>
              <strong className={styles.legendValue}>
                {valueLabel(last[field])}
              </strong>
            </span>
          );
        })}
      </div>
      <p className={styles.footnote}>
        Source: saved per-epoch {labels[field]?.toLowerCase() || field}
        {units[field] ? ` (${units[field]})` : ""}. Missing samples are omitted.
      </p>
    </figure>
  );
}
