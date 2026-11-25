import React, { useEffect, useRef, useState } from "react";
import "./signal.css";

const epochs = [1, 2, 3, 4, 5, 6, 7, 8];
const trainAccuracy = [52, 64, 72, 79, 84, 88, 91, 93];
const validationAccuracy = [47, 61, 68, 75, 78, 82, 84, 85];
const xAt = (index) => 54 + index * 65;
const yAt = (value) => 182 - ((value - 40) / 60) * 144;
const pathFor = (values) =>
  values
    .map((value, index) => `${index ? "L" : "M"}${xAt(index)} ${yAt(value)}`)
    .join(" ");
const readingAt = (values, progress) => {
  const index = Math.min(values.length - 1, Math.floor(progress));
  const next = Math.min(values.length - 1, index + 1);
  return values[index] + (values[next] - values[index]) * (progress - index);
};
const pathTo = (values, progress) => {
  const complete = values.slice(0, Math.floor(progress) + 1);
  const partial = progress % 1;
  const path = pathFor(complete);
  return partial && complete.length < values.length
    ? `${path} L${54 + progress * 65} ${yAt(readingAt(values, progress))}`
    : path;
};

export default function Signal() {
  const reducedMotion = useRef(
    window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  // Starts static at epoch 7 with full trajectory; user can scrub by hover/click or toggle play
  const [progress, setProgress] = useState(7);
  const [playing, setPlaying] = useState(false);
  const progressRef = useRef(progress);
  const inspectingRef = useRef(false);

  useEffect(() => {
    if (!playing || reducedMotion.current) return;
    let frame;
    let previous;
    let painted = 0;
    const advance = (time) => {
      const delta = previous === undefined ? 0 : Math.min(64, time - previous);
      previous = time;
      if (!document.hidden && !inspectingRef.current) {
        const next = progressRef.current + delta / 1300;
        progressRef.current = next >= 7.9 ? 0 : next;
        if (time - painted >= 32) {
          setProgress(Math.min(7, progressRef.current));
          painted = time;
        }
      }
      frame = requestAnimationFrame(advance);
    };
    frame = requestAnimationFrame(advance);
    return () => cancelAnimationFrame(frame);
  }, [playing]);

  const epoch = Math.min(7, Math.floor(progress));
  const train = Math.round(readingAt(trainAccuracy, progress));
  const validation = Math.round(readingAt(validationAccuracy, progress));
  const gap = train - validation;
  const cursorX = 54 + progress * 65;
  const inspect = (event) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width) * 560;
    const next = Math.max(0, Math.min(7, (x - 54) / 65));
    progressRef.current = next;
    setProgress(next);
  };
  return (
    <div
      className="tt-signal"
      aria-label="Illustrative training progress preview"
    >
      <div className="tt-signal-top">
        <div>
          <span className="tt-signal-live-dot" aria-hidden="true" />
          <strong>Training in context</strong>
          <span className="tt-signal-run">RUN / MNIST - RESNET-18</span>
        </div>
        <span className="tt-signal-demo">
          Illustrative data · no run is active here
        </span>
      </div>
      <div className="tt-signal-layout">
        <div className="tt-signal-chart">
          <div className="tt-signal-chart-title">
            <div>
              <small>LEARNING TRAJECTORY</small>
              <h3>Accuracy across epochs</h3>
            </div>
            <span>Higher is better</span>
          </div>
          <svg
            viewBox="0 0 560 230"
            role="img"
            aria-label={`Illustrative training accuracy ${train} percent and validation accuracy ${validation} percent near epoch ${epoch + 1}. Use arrow keys to inspect epochs.`}
            tabIndex={0}
            onPointerEnter={() => {
              inspectingRef.current = true;
            }}
            onPointerMove={inspect}
            onPointerLeave={() => {
              inspectingRef.current = false;
            }}
            onKeyDown={(event) => {
              if (event.key !== "ArrowLeft" && event.key !== "ArrowRight")
                return;
              event.preventDefault();
              setPlaying(false);
              const next = Math.max(
                0,
                Math.min(
                  7,
                  Math.round(progressRef.current) +
                    (event.key === "ArrowRight" ? 1 : -1),
                ),
              );
              progressRef.current = next;
              setProgress(next);
            }}
          >
            <defs>
              <linearGradient id="tt-hero-area" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#45adf0" stopOpacity=".18" />
                <stop offset="100%" stopColor="#45adf0" stopOpacity="0" />
              </linearGradient>
            </defs>
            {[40, 60, 80, 100].map((value) => (
              <g key={value}>
                <line
                  x1="54"
                  x2="515"
                  y1={yAt(value)}
                  y2={yAt(value)}
                  className="tt-signal-grid"
                />
                <text x="4" y={yAt(value) + 4} className="tt-signal-axis">
                  {value}%
                </text>
              </g>
            ))}
            {/* Full reference trajectories so the chart never looks empty */}
            <path
              d={pathFor(trainAccuracy)}
              className="tt-signal-ghost-line tt-signal-ghost-train"
            />
            <path
              d={pathFor(validationAccuracy)}
              className="tt-signal-ghost-line tt-signal-ghost-validation"
            />
            <path
              d={`${pathTo(trainAccuracy, progress)} L${cursorX} 182 L54 182 Z`}
              fill="url(#tt-hero-area)"
            />
            <path
              d={pathTo(trainAccuracy, progress)}
              className="tt-signal-line tt-signal-train"
            />
            <path
              d={pathTo(validationAccuracy, progress)}
              className="tt-signal-line tt-signal-validation"
            />
            <line
              x1={cursorX}
              x2={cursorX}
              y1="25"
              y2="188"
              className="tt-signal-cursor"
            />
            <circle
              cx={cursorX}
              cy={yAt(readingAt(trainAccuracy, progress))}
              r="5"
              className="tt-signal-marker tt-signal-train-marker"
            />
            <circle
              cx={cursorX}
              cy={yAt(readingAt(validationAccuracy, progress))}
              r="5"
              className="tt-signal-marker tt-signal-validation-marker"
            />
            {epochs.map((epNum, index) => (
              <text
                key={epNum}
                x={xAt(index)}
                y="215"
                textAnchor="middle"
                className={`tt-signal-axis tt-signal-epoch-label ${
                  Math.round(progress) === index ? "is-active-epoch" : ""
                }`}
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setPlaying(false);
                  progressRef.current = index;
                  setProgress(index);
                }}
              >
                {epNum}
              </text>
            ))}
          </svg>
          <div className="tt-signal-chart-foot">
            <div className="tt-signal-legend">
              <span>
                <i /> Training
              </span>
              <span>
                <i /> Validation
              </span>
            </div>
            <span>Epoch</span>
          </div>
        </div>
        <aside className="tt-signal-insight">
          <div className="tt-signal-insight-head">
            <small>SELECTED EPOCH</small>
            <strong>
              {String(epoch + 1).padStart(2, "0")} <span>/ 08</span>
            </strong>
          </div>
          <div className="tt-signal-reading">
            <span>Training accuracy</span>
            <strong>{train}%</strong>
          </div>
          <div className="tt-signal-reading">
            <span>Validation accuracy</span>
            <strong>{validation}%</strong>
          </div>
          <div className="tt-signal-reading">
            <span>Generalization gap</span>
            <strong>{gap} pp</strong>
          </div>
          <p>
            The gap shows how training and validation are separating. Inspect
            the full curves before choosing a checkpoint.
          </p>
          <button
            type="button"
            className="tt-signal-pause"
            onClick={() => setPlaying((value) => !value)}
            aria-label={
              playing ? "Pause example animation" : "Play example animation"
            }
          >
            {playing ? (
              <>
                <svg
                  className="tt-btn-svg"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  aria-hidden="true"
                  width="12"
                  height="12"
                >
                  <rect x="3" y="2.5" width="3.5" height="11" rx="1" />
                  <rect x="9.5" y="2.5" width="3.5" height="11" rx="1" />
                </svg>
                <span>Pause preview</span>
              </>
            ) : (
              <>
                <svg
                  className="tt-btn-svg"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  aria-hidden="true"
                  width="12"
                  height="12"
                >
                  <path d="M4 2.5a.75.75 0 0 0-1.15-.65L13.2 7.35a.75.75 0 0 1 0 1.3L2.85 14.15A.75.75 0 0 1 1.7 13.5V2.5z" />
                </svg>
                <span>Play preview</span>
              </>
            )}
          </button>
        </aside>
      </div>
    </div>
  );
}
