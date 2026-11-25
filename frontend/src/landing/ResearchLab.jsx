import "./research-lab.css";
import React, { useEffect, useState } from "react";
import Reveal from "./Reveal";

const signals = {
  accuracy: {
    label: "Validation accuracy",
    unit: "%",
    a: [42, 61, 73, 81, 86, 90, 93, 95],
    b: [39, 55, 66, 76, 82, 86, 89, 91],
  },
  loss: {
    label: "Validation loss",
    unit: "",
    a: [2.1, 1.6, 1.2, 0.9, 0.65, 0.48, 0.31, 0.22],
    b: [2.3, 1.9, 1.5, 1.1, 0.86, 0.68, 0.49, 0.36],
  },
};
function curve(values, max) {
  return values
    .map(
      (value, index) =>
        `${index ? "L" : "M"}${45 + index * 67},${215 - (value / max) * 175}`,
    )
    .join(" ");
}

export default function ResearchLab() {
  const [metric, setMetric] = useState("accuracy");
  // Full trajectory ready on load; interactive scrubber for user exploration
  const [epoch, setEpoch] = useState(7);
  const [showB, setShowB] = useState(true);
  const [playing, setPlaying] = useState(false);
  const data = signals[metric];
  const max = metric === "accuracy" ? 100 : 2.5;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setEpoch((value) => {
        if (value >= 7) {
          setPlaying(false);
          return 7;
        }
        return value + 1;
      });
    }, 650);
    return () => window.clearInterval(timer);
  }, [playing]);
  return (
    <Reveal className="tt-lab-section" id="live-view">
      <div className="tt-section-heading">
        <div>
          <div className="tt-kicker">LOOK INSIDE THE EXPERIMENT</div>
          <h2>
            The curve is the beginning
            <br />
            of a better question.
          </h2>
        </div>
        <p>
          Explore this illustrative comparison. Change the metric, inspect an
          epoch, and isolate a run—then take that same curiosity into your own
          workspace.
        </p>
      </div>
      <div className="tt-lab">
        <aside>
          <span className="tt-lab-brand">
            T<span> / TrainTrace</span>
          </span>
          <small>INVESTIGATION</small>
          <strong>Learning to recognize digits</strong>
          {[
            "Investigations",
            "Training",
            "Compare",
            "Decisions",
            "Registry",
            "Inference",
          ].map((name) => (
            <div key={name} className={name === "Compare" ? "is-current" : ""}>
              <span
                className={`tt-lab-nav-bullet ${name === "Compare" ? "is-active" : ""}`}
                aria-hidden="true"
              />
              {name}
            </div>
          ))}
          <p>
            Interactive illustration
            <br />
            No training job is launched.
          </p>
        </aside>
        <div className="tt-lab-main">
          <header>
            <div>
              <small>MNIST / MODEL COMPARISON</small>
              <h3>Two approaches. One question.</h3>
            </div>
            <span className="tt-example-tag">Example data</span>
          </header>
          <div className="tt-lab-controls">
            <div role="group" aria-label="Preview metric">
              {Object.entries(signals).map(([key, item]) => (
                <button
                  key={key}
                  aria-pressed={metric === key}
                  onClick={() => {
                    setMetric(key);
                    setEpoch(0);
                    setPlaying(
                      !window.matchMedia("(prefers-reduced-motion: reduce)")
                        .matches,
                    );
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <label>
              <input
                type="checkbox"
                checked={showB}
                onChange={(e) => setShowB(e.target.checked)}
              />{" "}
              Compare MobileNetV2
            </label>
          </div>
          <div className="tt-lab-chart">
            <svg
              viewBox="0 0 560 250"
              role="img"
              aria-label={`${data.label} comparison at epoch ${epoch + 1}`}
              onPointerMove={(event) => {
                if (event.pointerType === "touch") return;
                const bounds = event.currentTarget.getBoundingClientRect();
                const x = ((event.clientX - bounds.left) / bounds.width) * 560;
                if (x < 42 || x > 535) return;
                setPlaying(false);
                setEpoch(Math.max(0, Math.min(7, Math.round((x - 45) / 67))));
              }}
            >
              <defs>
                <linearGradient id="lab-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1683c9" stopOpacity=".23" />
                  <stop offset="100%" stopColor="#1683c9" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[40, 95, 155, 215].map((y, i) => (
                <g key={y}>
                  <line
                    x1="42"
                    x2="535"
                    y1={y}
                    y2={y}
                    stroke="currentColor"
                    opacity=".13"
                  />
                  <text
                    x="8"
                    y={y + 4}
                    fill="currentColor"
                    fontSize="10"
                    opacity=".6"
                  >
                    {metric === "accuracy"
                      ? [100, 67, 33, 0][i]
                      : [2.5, 1.7, 0.8, 0][i]}
                  </text>
                </g>
              ))}
              <path
                d={`${curve(data.a, max)} L514,215 L45,215Z`}
                fill="url(#lab-fill)"
              />
              <path
                className="tt-lab-line"
                key={metric}
                d={curve(data.a, max)}
                fill="none"
                stroke="#1683c9"
                strokeWidth="3"
              />
              {showB && (
                <path
                  className="tt-lab-line"
                  key={metric + "b"}
                  d={curve(data.b, max)}
                  fill="none"
                  stroke="#a36edf"
                  strokeWidth="3"
                  strokeDasharray="7 5"
                />
              )}
              <line
                x1={45 + epoch * 67}
                x2={45 + epoch * 67}
                y1="25"
                y2="215"
                stroke="currentColor"
                opacity=".3"
                strokeDasharray="3 4"
              />
              <circle
                cx={45 + epoch * 67}
                cy={215 - (data.a[epoch] / max) * 175}
                r="5"
                fill="#1683c9"
                stroke="var(--landing-card)"
                strokeWidth="2"
              />
              {showB && (
                <circle
                  cx={45 + epoch * 67}
                  cy={215 - (data.b[epoch] / max) * 175}
                  r="5"
                  fill="#a36edf"
                />
              )}
              {[0, 1, 2, 3, 4, 5, 6, 7].map((n) => (
                <text
                  key={n}
                  x={45 + n * 67}
                  y="240"
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize="10"
                  opacity=".6"
                >
                  {n + 1}
                </text>
              ))}
            </svg>
          </div>
          <label className="tt-epoch-slider">
            Inspect epoch <strong>{epoch + 1}</strong>
            <input
              aria-label="Inspect illustrative epoch"
              type="range"
              min="0"
              max="7"
              value={epoch}
              onChange={(e) => {
                setPlaying(false);
                setEpoch(Number(e.target.value));
              }}
            />
          </label>
          <button
            className="tt-lab-replay"
            type="button"
            onClick={() => {
              setEpoch(0);
              setPlaying(
                !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
              );
            }}
          >
            {playing ? "Playing example…" : "Replay curve"}
          </button>
          <div className="tt-lab-results">
            <div>
              <i /> ResNet-18{" "}
              <strong>
                {data.a[epoch]}
                {data.unit}
              </strong>
            </div>
            {showB && (
              <div>
                <i /> MobileNetV2{" "}
                <strong>
                  {data.b[epoch]}
                  {data.unit}
                </strong>
              </div>
            )}
            <p>
              Same dataset. Compare learning behavior before selecting a
              candidate.
            </p>
          </div>
        </div>
      </div>
    </Reveal>
  );
}
