import React from "react";
const colors = ["#2563eb", "#047857", "#b45309", "#a21caf"];
export default function MetricChart({ runs, field, title }) {
  const series = runs.filter((r) => r.metrics?.length);
  if (!series.length)
    return (
      <div className="empty">
        {runs.length
          ? "No persisted epoch metrics yet."
          : "Select candidate runs to compare their trajectories."}
      </div>
    );
  const values = series.flatMap((r) => r.metrics.map((m) => m[field]));
  const low = Math.min(0, ...values),
    high = Math.max(...values, 1),
    epochs = Math.max(1, ...series.map((r) => r.metrics.length));
  const x = (e) => 45 + ((e - 1) / Math.max(1, epochs - 1)) * 615,
    y = (v) => 190 - ((v - low) / (high - low)) * 160;
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg
        viewBox="0 0 700 230"
        role="img"
        aria-label={`${title}, ${series.length} runs. Exact values available in epoch table.`}
      >
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line
              x1="45"
              x2="660"
              y1={30 + t * 160}
              y2={30 + t * 160}
              stroke="#dce3ed"
            />
            <text x="2" y={34 + t * 160}>
              {(high - t * (high - low)).toFixed(1)}
            </text>
          </g>
        ))}
        {series.map((r, i) => (
          <g key={r.id}>
            <polyline
              fill="none"
              stroke={colors[i % 4]}
              strokeWidth="2.5"
              points={r.metrics
                .map((m) => `${x(m.epoch)},${y(m[field])}`)
                .join(" ")}
            />
            {r.metrics.map((m) => (
              <circle
                key={m.id}
                cx={x(m.epoch)}
                cy={y(m[field])}
                r="3"
                fill={colors[i % 4]}
              >
                <title>
                  {r.approach_name}: epoch {m.epoch}, {m[field]}
                </title>
              </circle>
            ))}
          </g>
        ))}
        <text x="45" y="218">
          Epoch 1
        </text>
        <text x="590" y="218">
          Epoch {epochs}
        </text>
      </svg>
      <div className="legend">
        {series.map((r, i) => (
          <span key={r.id} style={{ color: colors[i % 4] }}>
            {r.approach_name}
          </span>
        ))}
      </div>
    </figure>
  );
}
