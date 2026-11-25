import React, { useEffect, useRef, useState } from "react";
import Reveal from "./Reveal";
import { stages, capabilities } from "./productContent";

export function ProblemSection() {
  const problemIcons = [
    // Score without context
    <svg
      key="icon-ctx"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      width="22"
      height="22"
      className="tt-problem-icon"
      aria-hidden="true"
    >
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      <line
        x1="2"
        y1="2"
        x2="22"
        y2="22"
        strokeWidth="2"
        stroke="currentColor"
      />
    </svg>,
    // Run you cannot see
    <svg
      key="icon-see"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      width="22"
      height="22"
      className="tt-problem-icon"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line
        x1="1"
        y1="1"
        x2="23"
        y2="23"
        strokeWidth="2"
        stroke="currentColor"
      />
    </svg>,
    // Decision you cannot revisit
    <svg
      key="icon-rev"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      width="22"
      height="22"
      className="tt-problem-icon"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 8 14" />
      <path d="M2.5 12a9.5 9.5 0 0 1 15-7.5L20 7M20 3v4h-4" />
    </svg>,
  ];

  return (
    <Reveal className="tt-problem">
      <div className="tt-kicker">WHY TRAINTRACE EXISTS</div>
      <h2>
        Which model is better?
        <br />
        <span>Deserves more than one number.</span>
      </h2>
      <div className="tt-problem-grid">
        {[
          [
            "A score without context",
            "A validation result means less when the split, configuration, and checkpoint are scattered across files.",
          ],
          [
            "A run you cannot see",
            "Waiting for a final score hides the learning curve, performance bottlenecks, and early signs of overfitting.",
          ],
          [
            "A decision you cannot revisit",
            "When the reasoning is lost, every new experiment starts with the same unanswered questions.",
          ],
        ].map(([title, text], idx) => (
          <article key={title} className="tt-problem-card">
            <div className="tt-problem-icon-wrap">{problemIcons[idx]}</div>
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </Reveal>
  );
}

export function WorkflowShowcase() {
  const [selected, setSelected] = useState(0);
  const trackRef = useRef(null);
  const stage = stages[selected];

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const track = trackRef.current;
    if (!track) return;

    let ticking = false;
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const rect = track.getBoundingClientRect();
          const trackHeight = rect.height - window.innerHeight;
          if (trackHeight > 0) {
            const scrolled = -rect.top;
            const progress = Math.max(
              0,
              Math.min(0.999, scrolled / trackHeight),
            );
            const newIndex = Math.min(
              stages.length - 1,
              Math.floor(progress * stages.length),
            );
            setSelected(newIndex);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const jumpToStage = (index) => {
    setSelected(index);
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const trackTop = window.scrollY + rect.top;
    const trackHeight = rect.height - window.innerHeight;
    const targetScroll = trackTop + (index / stages.length) * trackHeight + 20;
    window.scrollTo({ top: targetScroll, behavior: "smooth" });
  };

  return (
    <div className="tt-showcase-scroll-track" ref={trackRef}>
      <div className="tt-showcase-sticky-container">
        <div className="tt-showcase-inner">
          <div className="tt-kicker">ONE CONNECTED RESEARCH WORKFLOW</div>
          <h2>
            From a hypothesis
            <br />
            to evidence you can inspect.
          </h2>
          <div className="tt-stage-nav-wrap">
            <div
              className="tt-stage-tabs"
              role="tablist"
              aria-label="Explore workflow"
            >
              {stages.map((item, index) => (
                <button
                  key={item.title}
                  id={`stage-tab-${index}`}
                  role="tab"
                  aria-selected={selected === index}
                  aria-controls="stage-panel"
                  tabIndex={selected === index ? 0 : -1}
                  onClick={() => jumpToStage(index)}
                >
                  {String(index + 1).padStart(2, "0")} <span>{item.title}</span>
                </button>
              ))}
            </div>
            <div className="tt-scroll-indicator-pill">
              <span className="tt-scroll-pulse-dot" aria-hidden="true" />
              <span>Scroll to advance stages</span>
              <svg
                viewBox="0 0 16 16"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M8 3v10M4 9l4 4 4-4" />
              </svg>
            </div>
          </div>
          <div
            id="stage-panel"
            role="tabpanel"
            aria-labelledby={`stage-tab-${selected}`}
            className="tt-stage-panel"
            key={selected}
          >
            <div>
              <h3>{stage.label}</h3>
              <p>{stage.text}</p>
            </div>
            <div className="tt-mini-window">
              <header>
                <div className="tt-window-mac-dots" aria-hidden="true">
                  <span className="dot-red" />
                  <span className="dot-yellow" />
                  <span className="dot-green" />
                </div>
                <span>TrainTrace / {stage.title}</span>
                <small>Illustrative workflow</small>
              </header>
              {stage.rows.map(([label, value]) => (
                <div className="tt-preview-row" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
              {(selected === 1 || selected === 2) && (
                <div
                  className="tt-workflow-chart"
                  aria-label="Illustrative validation accuracy curves across five epochs"
                >
                  <div className="tt-workflow-chart-head">
                    <span>Validation accuracy</span>
                    <span className="tt-workflow-chart-key">
                      <i /> Candidate A <i /> Candidate B
                    </span>
                  </div>
                  <svg
                    viewBox="0 0 600 148"
                    role="img"
                    aria-label="Two illustrative accuracy curves improve across five epochs"
                  >
                    <path
                      className="tt-workflow-grid"
                      d="M36 18H586M36 66H586M36 114H586"
                    />
                    <text x="2" y="22">
                      100
                    </text>
                    <text x="10" y="70">
                      80
                    </text>
                    <text x="10" y="118">
                      60
                    </text>
                    <path
                      className="tt-workflow-line tt-workflow-line-a"
                      d="M38 112 L174 75 L310 49 L446 32 L584 22"
                    />
                    <path
                      className="tt-workflow-line tt-workflow-line-b"
                      d="M38 120 L174 89 L310 67 L446 51 L584 41"
                    />
                    <circle
                      className="tt-workflow-dot-a"
                      cx="584"
                      cy="22"
                      r="4"
                    />
                    <circle
                      className="tt-workflow-dot-b"
                      cx="584"
                      cy="41"
                      r="4"
                    />
                    <text x="36" y="144">
                      Epoch 1
                    </text>
                    <text x="530" y="144">
                      Epoch 5
                    </text>
                  </svg>
                  <small>
                    Illustrative curves; live measurements appear in the
                    workspace.
                  </small>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CapabilitiesSection() {
  const bentoVisuals = [
    // 01 Lineage & investigations
    <div className="tt-bento-visual tt-visual-lineage" key="bento-0">
      <span className="tt-bento-chip">Hypothesis</span>
      <svg
        className="tt-bento-arrow"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        width="10"
        height="10"
        aria-hidden="true"
      >
        <path d="M6 3l5 5-5 5" />
      </svg>
      <span className="tt-bento-chip is-accent">Run 04 (ResNet-18)</span>
      <svg
        className="tt-bento-arrow"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        width="10"
        height="10"
        aria-hidden="true"
      >
        <path d="M6 3l5 5-5 5" />
      </svg>
      <span className="tt-bento-chip is-success">Registered v1</span>
    </div>,

    // 02 Five image datasets
    <div className="tt-bento-visual tt-visual-chips" key="bento-1">
      {["MNIST", "CIFAR-10", "CIFAR-100", "Fashion-MNIST", "SVHN"].map(
        (name) => (
          <span key={name} className="tt-bento-badge">
            {name}
          </span>
        ),
      )}
    </div>,

    // 03 Four model families
    <div className="tt-bento-visual tt-visual-models" key="bento-2">
      <div className="tt-bento-model-row">
        <span>ResNet-18</span>
        <small>11.2M params - ImageNet init</small>
      </div>
      <div className="tt-bento-model-row">
        <span>MobileNetV2</span>
        <small>2.2M params - Inverted residuals</small>
      </div>
      <div className="tt-bento-model-row">
        <span>EfficientNet-B0</span>
        <small>4.0M params - Compound scaling</small>
      </div>
    </div>,

    // 04 Live charts & exports
    <div className="tt-bento-visual tt-visual-spark" key="bento-3">
      <svg
        viewBox="0 0 200 36"
        width="100%"
        height="26"
        fill="none"
        className="tt-sparkline"
        aria-hidden="true"
      >
        <path
          d="M0 30 Q 40 26, 75 16 T 140 8 T 200 4"
          stroke="#45adf0"
          strokeWidth="2"
        />
        <path
          d="M0 34 Q 40 30, 75 22 T 140 15 T 200 10"
          stroke="#a36edf"
          strokeWidth="1.8"
          strokeDasharray="3 3"
        />
      </svg>
      <div className="tt-spark-label">
        <span>Loss stream</span>
        <span>Accuracy curve</span>
        <span>CSV export</span>
      </div>
    </div>,

    // 05 Reproducibility audits
    <div className="tt-bento-visual tt-visual-audit" key="bento-4">
      <div className="tt-audit-pill">
        <span className="tt-audit-dot" aria-hidden="true" />
        <code>seed: 42 - deterministic split identity</code>
      </div>
      <span className="tt-audit-status">Replay Status: Bit-Identical</span>
    </div>,

    // 06 Final evaluation reports
    <div className="tt-bento-visual tt-visual-matrix" key="bento-5">
      <div className="tt-matrix-mini">
        <span className="is-high">98.2%</span>
        <span className="is-low">0.8%</span>
        <span className="is-low">1.1%</span>
        <span className="is-high">96.5%</span>
      </div>
      <small>Held-out confusion matrix & class metrics</small>
    </div>,

    // 07 Registry & image inference
    <div className="tt-bento-visual tt-visual-inference" key="bento-6">
      <div className="tt-inference-row">
        <span>Test Sample: Digit 7</span>
        <div className="tt-bar-track">
          <div className="tt-bar-fill" style={{ width: "99.4%" }} />
        </div>
        <strong className="tt-conf">99.4%</strong>
      </div>
    </div>,

    // 08 Notebook & artifact access
    <div className="tt-bento-visual tt-visual-code" key="bento-7">
      <code>traintrace export --run=run_08.ipynb</code>
    </div>,

    // 09 Search & research history
    <div className="tt-bento-visual tt-visual-search" key="bento-8">
      <span className="tt-search-tag">tag:baseline</span>
      <span className="tt-search-tag">val_acc &gt; 90%</span>
      <span className="tt-search-kbd">Filter</span>
    </div>,
  ];

  return (
    <Reveal className="tt-capabilities" id="features">
      <div className="tt-kicker">THE TOOLS AROUND THE TRAINING LOOP</div>
      <h2>Keep the whole experiment in view.</h2>
      <div className="tt-capability-grid">
        {capabilities.map(([title, text], index) => (
          <article key={title} className="tt-bento-card">
            <div className="tt-bento-head">
              <span className="tt-feature-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{title}</h3>
            </div>
            <p>{text}</p>
            <div className="tt-bento-footer-wrap">{bentoVisuals[index]}</div>
          </article>
        ))}
      </div>
    </Reveal>
  );
}

export function ExecutionSection() {
  return (
    <Reveal className="tt-execution">
      <div>
        <div className="tt-kicker">CHOOSE WHERE COMPUTE HAPPENS</div>
        <h2>
          Local execution.
          <br />A path to cloud GPUs.
        </h2>
        <p>
          Train locally and inspect measurements in the workspace. The Kaggle
          integration submits a generated training script and brings remote
          readings and artifacts back into the same run.
        </p>
      </div>
      <div className="tt-execution-map">
        <div className="tt-execution-node tt-node-workspace">
          <div className="tt-node-top-row">
            <div className="tt-node-header">
              <span className="tt-node-dot" aria-hidden="true" />
              <strong>Local Workspace & State Store</strong>
              <span className="tt-node-pill">Controller</span>
            </div>
            <div className="tt-node-tags">
              <span>SQLite Database</span>
              <span>Artifact Store</span>
              <span>Stream Hub</span>
            </div>
          </div>
          <p className="tt-node-desc">
            Single local source of truth for experiment lineage, metrics, and
            checkpoint records.
          </p>
        </div>

        <div className="tt-execution-bridge">
          <div className="tt-bridge-channel is-dispatch">
            <div className="tt-bridge-label">
              <svg
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                width="12"
                height="12"
                aria-hidden="true"
              >
                <path d="M8 3v10M4 9l4 4 4-4" />
              </svg>
              <span>Dispatch Code & Hyperparameters</span>
            </div>
            <small>Tarball bundle · config payload</small>
          </div>

          <div className="tt-bridge-badge">
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              width="12"
              height="12"
              aria-hidden="true"
            >
              <path d="M3 8h10M8 3v10" />
            </svg>
            <span>Real-time Telemetry Bridge</span>
          </div>

          <div className="tt-bridge-channel is-telemetry">
            <div className="tt-bridge-label">
              <svg
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                width="12"
                height="12"
                aria-hidden="true"
              >
                <path d="M8 13V3M4 7l4-4 4 4" />
              </svg>
              <span>Stream Metrics & Checkpoints</span>
            </div>
            <small>WebSocket loss · weight pullback</small>
          </div>
        </div>

        <div className="tt-execution-targets">
          <div className="tt-execution-node tt-node-target">
            <div className="tt-target-header">
              <div className="tt-target-icon-wrap is-cyan">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="18"
                  height="18"
                  aria-hidden="true"
                >
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                  <rect x="9" y="9" width="6" height="6" />
                  <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />
                </svg>
              </div>
              <div>
                <strong>Local Workstation</strong>
                <span className="tt-target-badge">Direct Execution</span>
              </div>
            </div>
            <div className="tt-target-specs">
              <div className="tt-spec-item">
                <span className="tt-spec-k">Runtime</span>
                <span className="tt-spec-v">PyTorch 2.6</span>
              </div>
              <div className="tt-spec-item">
                <span className="tt-spec-k">Hardware</span>
                <span className="tt-spec-v">MPS / CUDA / CPU</span>
              </div>
              <div className="tt-spec-item">
                <span className="tt-spec-k">Latency</span>
                <span className="tt-spec-v">&lt; 1ms batch stream</span>
              </div>
            </div>
            <p className="tt-target-desc">
              Executes on local hardware with zero setup, immediate terminal
              output, and instant checkpoint writes.
            </p>
          </div>

          <div className="tt-execution-node tt-node-target">
            <div className="tt-target-header">
              <div className="tt-target-icon-wrap is-purple">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="18"
                  height="18"
                  aria-hidden="true"
                >
                  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
                </svg>
              </div>
              <div>
                <strong>Kaggle Cloud GPU</strong>
                <span className="tt-target-badge is-cloud">
                  Tesla T4 · 16GB
                </span>
              </div>
            </div>
            <div className="tt-target-specs">
              <div className="tt-spec-item">
                <span className="tt-spec-k">Runtime</span>
                <span className="tt-spec-v">Remote Kernel Worker</span>
              </div>
              <div className="tt-spec-item">
                <span className="tt-spec-k">Hardware</span>
                <span className="tt-spec-v">NVIDIA Tesla T4 GPU</span>
              </div>
              <div className="tt-spec-item">
                <span className="tt-spec-k">Sync</span>
                <span className="tt-spec-v">Artifact auto-pullback</span>
              </div>
            </div>
            <p className="tt-target-desc">
              Packages code into a self-contained bundle, pushes to Kaggle via
              API, and streams progress back live.
            </p>
          </div>
        </div>

        <div className="tt-execution-footer-bar">
          <div className="tt-guarantee-badge">
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              width="14"
              height="14"
              aria-hidden="true"
            >
              <path d="M8 2l5 2v4c0 3.5-2.5 6.5-5 7-2.5-.5-5-3.5-5-7V4l5-2z" />
              <path d="M6 8l1.5 1.5L10 6" />
            </svg>
            <span>
              Deterministic environment guarantee across both workstation and
              cloud targets
            </span>
          </div>
          <span className="tt-api-badge">Kaggle API v1.6 Verified</span>
        </div>
      </div>
    </Reveal>
  );
}

export function FaqSection() {
  return (
    <Reveal className="tt-faq" id="faq">
      <div className="tt-kicker">BEFORE YOUR FIRST RUN</div>
      <h2>A few useful answers.</h2>
      <div className="tt-faq-list">
        {[
          [
            "Are the models trained here?",
            "Yes. The selected architecture is trained using your run settings. Supported architectures can optionally initialize with ImageNet weights; CustomCNN starts from random weights.",
          ],
          [
            "What is the notebook for?",
            "The analysis notebook reads saved evidence. The exported training notebook contains the run configuration and training code for continuing outside the dashboard. Remote notebook execution does not automatically imply a live connection to your local app.",
          ],
          [
            "Is prediction confidence the same as accuracy?",
            "No. Confidence describes one prediction. Dataset accuracy measures performance across labeled examples. An uploaded image can differ from the images used during training.",
          ],
          [
            "Why separate validation and final evaluation?",
            "Validation guides comparison and checkpoint selection. A separate final test partition helps you assess the selected candidate without repeatedly using test results to tune it.",
          ],
        ].map(([title, text]) => (
          <details key={title} className="tt-faq-item">
            <summary className="tt-faq-summary">
              <span className="tt-faq-title">{title}</span>
              <span className="tt-faq-icon" aria-hidden="true">
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="13"
                  height="13"
                >
                  <path d="M4 6l4 4 4-4" />
                </svg>
              </span>
            </summary>
            <div className="tt-faq-content">
              <p>{text}</p>
            </div>
          </details>
        ))}
      </div>
    </Reveal>
  );
}
