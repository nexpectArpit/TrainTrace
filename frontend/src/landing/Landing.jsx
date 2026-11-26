import React, { useEffect, useState } from "react";
import "./landing.css";
import {
  ProblemSection,
  WorkflowShowcase,
  CapabilitiesSection,
  ExecutionSection,
  FaqSection,
} from "./ProductStory";
import FeatureExplorer from "./FeatureExplorer";
import ResearchLab from "./ResearchLab";
import Signal from "./Signal";
import useLandingMotion from "./useLandingMotion";
import "./landing-premium.css";
import "./landing-refinement.css";

const chapters = [
  [
    "01",
    "Ask a better question.",
    "Start with an investigation. Give each experiment an objective, a hypothesis, and a reason to exist.",
  ],
  [
    "02",
    "Watch learning happen.",
    "Follow batch loss, accuracy, throughput, and available system measurements as your run progresses.",
  ],
  [
    "03",
    "Compare the evidence.",
    "Put runs beside each other. Explore their curves, inspect configurations, and understand the trade-offs.",
  ],
  [
    "04",
    "Leave a trace.",
    "Keep your decisions connected to validation results, saved checkpoints, and the next question.",
  ],
];

export default function Landing() {
  useLandingMotion();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);
  const openDashboard = (event, path = "/dashboard/investigations") => {
    event.preventDefault();
    closeMenu();
    window.history.pushState(null, "", path);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  const scrollToSection = (id) => {
    closeMenu();
    document.getElementById(id)?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "start",
    });
  };
  useEffect(() => {
    if (location.hash) {
      history.replaceState(null, "", location.pathname + location.search);
    }
  }, []);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);
  return (
    <div className="tt-landing tt-dark" id="top">
      <nav className="tt-nav" aria-label="Main navigation">
        <button
          className="tt-brand-link"
          type="button"
          aria-label="TrainTrace home"
          onClick={() => scrollToSection("top")}
        >
          <img src="/brand/traintrace-logo-dark.png" alt="TrainTrace" />
        </button>
        <div
          className={`tt-nav-links${menuOpen ? " is-open" : ""}`}
          id="tt-landing-menu"
        >
          <button type="button" onClick={() => scrollToSection("workflow")}>
            Workflow
          </button>
          <button type="button" onClick={() => scrollToSection("live-view")}>
            Live view
          </button>
          <button type="button" onClick={() => scrollToSection("features")}>
            Features
          </button>
          <button type="button" onClick={() => scrollToSection("evidence")}>
            Evidence
          </button>
          <button type="button" onClick={() => scrollToSection("faq")}>
            FAQ
          </button>
        </div>
        <a
          className="tt-nav-cta"
          href="/dashboard/investigations"
          onClick={(e) => openDashboard(e, "/dashboard/investigations")}
        >
          <span>Open Workspace</span>
          <svg
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            width="12"
            height="12"
          >
            <path d="M4 12L12 4M12 4H6M12 4V10" />
          </svg>
        </a>
        <button
          className="tt-menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="tt-landing-menu"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              width="20"
              height="20"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              width="20"
              height="20"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </nav>
      <main>
        <section className="tt-hero">
          <div className="tt-atmosphere" aria-hidden="true">
            <span className="tt-atmosphere-grid" />
            <span className="tt-atmosphere-light tt-atmosphere-light-a" />
            <span className="tt-atmosphere-light tt-atmosphere-light-b" />
          </div>
          <div className="tt-kicker">
            <span /> BUILT FOR THE QUESTION AFTER THE SCORE
          </div>
          <h1>
            Your model learned.
            <br />
            <em>Understand how.</em>
          </h1>
          <div className="tt-hero-bottom">
            <p>
              Turn training runs into a research story. Live signals, clear
              comparisons, and decisions you can trace back to the evidence.
            </p>
            <div className="tt-hero-actions">
              <a
                className="tt-primary"
                href="/dashboard/investigations"
                onClick={(e) => openDashboard(e, "/dashboard/investigations")}
              >
                <span>Start investigating</span>
                <svg
                  className="tt-icon-arrow"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                  width="14"
                  height="14"
                >
                  <path d="M4 12L12 4M12 4H6M12 4V10" />
                </svg>
              </a>
              <button
                type="button"
                className="tt-secondary-btn"
                onClick={() => scrollToSection("live-view")}
              >
                <span>Inspect live preview</span>
                <svg
                  className="tt-icon-down"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                  width="14"
                  height="14"
                >
                  <path d="M3 6l5 5 5-5" />
                </svg>
              </button>
            </div>
          </div>
          <Signal />
          <div className="tt-caption">
            <span>FROM FIRST BATCH</span>
            <span>TO AN INFORMED NEXT STEP</span>
          </div>
        </section>
        <ProblemSection />
        <section className="tt-intro" id="workflow">
          <div className="tt-kicker">A WORKFLOW WITH A MEMORY</div>
          <h2>
            A number is a result.
            <br />
            <span>The trace is understanding.</span>
          </h2>
          <p>
            Training is only one part of the experiment. Keep the question, the
            process, and the reasoning connected.
          </p>
        </section>
        <section className="tt-chapters" aria-label="Research workflow">
          {chapters.map(([number, title, description], index) => (
            <article
              className="tt-chapter"
              key={number}
              style={{ "--card-index": index }}
            >
              <div className="tt-chapter-content">
                <span className="tt-number">{number}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
              <span className="tt-chapter-arrow" aria-hidden="true">
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="14"
                  height="14"
                >
                  <path d="M4 12L12 4M12 4H6M12 4V10" />
                </svg>
              </span>
            </article>
          ))}
        </section>
        <WorkflowShowcase />
        <ResearchLab />
        <CapabilitiesSection />
        <FeatureExplorer />
        <section className="tt-evidence" id="evidence">
          <div className="tt-evidence-header">
            <div>
              <span className="tt-kicker">MADE TO BE INSPECTED</span>
              <h2>
                Your work.
                <br />
                With the receipts.
              </h2>
            </div>
            <div className="tt-evidence-intro-text">
              <p>
                Keep configurations, epoch metrics, dataset splits, and
                checkpoint artifacts attached to the run that produced them.
              </p>
              <p>
                Inspect saved evidence in the workspace or continue your
                analysis in a notebook with guaranteed reproducibility.
              </p>
            </div>
          </div>
          <div
            className="tt-receipt-card"
            role="region"
            aria-label="Cryptographic Evidence Receipt"
          >
            <div className="tt-receipt-top">
              <div className="tt-receipt-status">
                <span className="tt-receipt-verified-dot" aria-hidden="true" />
                <strong>CRYPTOGRAPHIC PROVENANCE RECEIPT</strong>
              </div>
              <span className="tt-receipt-badge">VERIFIED DETERMINISTIC</span>
            </div>
            <div className="tt-receipt-body">
              <div className="tt-receipt-row">
                <span className="tt-receipt-label">RUN IDENTIFIER</span>
                <code className="tt-receipt-val">
                  run_20261119_resnet18_mnist_seed42
                </code>
              </div>
              <div className="tt-receipt-row">
                <span className="tt-receipt-label">CHECKPOINT SHA-256</span>
                <code className="tt-receipt-val tt-receipt-hash">
                  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                </code>
              </div>
              <div className="tt-receipt-grid">
                <div className="tt-receipt-item">
                  <span className="tt-receipt-sublabel">
                    DATASET SPLIT HASH
                  </span>
                  <strong>sha256:7f83b165... (80/20 seed 42)</strong>
                </div>
                <div className="tt-receipt-item">
                  <span className="tt-receipt-sublabel">BEST VAL ACCURACY</span>
                  <strong className="tt-receipt-highlight">
                    93.42% (Epoch 08)
                  </strong>
                </div>
                <div className="tt-receipt-item">
                  <span className="tt-receipt-sublabel">EXECUTION ENGINE</span>
                  <strong>PyTorch 2.6 - MPS / Kaggle T4</strong>
                </div>
                <div className="tt-receipt-item">
                  <span className="tt-receipt-sublabel">AUDIT STATUS</span>
                  <strong>Replay verified: Bit-identical</strong>
                </div>
              </div>
            </div>
            <div className="tt-receipt-footer">
              <span>
                Saved Artifacts: model.pt, metrics.csv, confusion_matrix.png,
                report.pdf
              </span>
              <span className="tt-receipt-sig">HMAC-SHA256 SIGNED</span>
            </div>
          </div>
        </section>
        <ExecutionSection />
        <FaqSection />
        <section className="tt-finale">
          <div className="tt-atmosphere" aria-hidden="true">
            <span className="tt-atmosphere-grid" />
            <span className="tt-atmosphere-light tt-atmosphere-light-a" />
            <span className="tt-atmosphere-light tt-atmosphere-light-b" />
          </div>
          <span className="tt-kicker">THE NEXT QUESTION IS YOURS</span>
          <h2>
            Make your next run
            <br />
            <em>mean something.</em>
          </h2>
          <a
            className="tt-primary"
            href="/dashboard/investigations"
            onClick={(e) => openDashboard(e, "/dashboard/investigations")}
          >
            <span>Open TrainTrace workspace</span>
            <svg
              className="tt-icon-arrow"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              width="14"
              height="14"
            >
              <path d="M4 12L12 4M12 4H6M12 4V10" />
            </svg>
          </a>
          <p>Your experiments and saved runs are inside.</p>
        </section>
      </main>
      <footer className="tt-footer">
        <div className="tt-footer-grid">
          <div className="tt-footer-brand">
            <span className="tt-wordmark">
              Train<span>Trace</span>
            </span>
            <p>
              Autonomous machine learning experiment tracing, live training
              telemetry, and verifiable decision evidence.
            </p>
            <div className="tt-footer-engine-badge">
              <span className="tt-footer-badge-dot" aria-hidden="true" />
              <span>Local Hardware & Kaggle GPU Cloud Ready</span>
            </div>
          </div>
          <div className="tt-footer-links-group">
            <strong>Platform</strong>
            <button type="button" onClick={() => scrollToSection("workflow")}>
              Workflow Lineage
            </button>
            <button type="button" onClick={() => scrollToSection("live-view")}>
              Live Signal Chart
            </button>
            <button type="button" onClick={() => scrollToSection("features")}>
              Capability Suite
            </button>
            <button type="button" onClick={() => scrollToSection("evidence")}>
              Cryptographic Evidence
            </button>
          </div>
          <div className="tt-footer-links-group">
            <strong>Supported Models</strong>
            <span>ResNet-18 (ImageNet init)</span>
            <span>MobileNetV2 (Edge optimized)</span>
            <span>EfficientNet-B0 (Compound scale)</span>
            <span>CustomCNN (Configurable)</span>
          </div>
          <div className="tt-footer-links-group">
            <strong>Workflows</strong>
            <a
              href="/dashboard/training"
              className="tt-footer-link"
              onClick={(e) => openDashboard(e, "/dashboard/training")}
            >
              Training Dashboard
            </a>
            <a
              href="/dashboard/compare"
              className="tt-footer-link"
              onClick={(e) => openDashboard(e, "/dashboard/compare")}
            >
              Model Comparison
            </a>
            <a
              href="/dashboard/registry"
              className="tt-footer-link"
              onClick={(e) => openDashboard(e, "/dashboard/registry")}
            >
              Model Registry
            </a>
            <a
              href="/dashboard/audits"
              className="tt-footer-link"
              onClick={(e) => openDashboard(e, "/dashboard/audits")}
            >
              Audit Lineage
            </a>
          </div>
        </div>
        <div className="tt-footer-bottom">
          <span>TrainTrace - Built for the question after the score.</span>
          <button
            type="button"
            className="tt-back-top-btn"
            onClick={() => scrollToSection("top")}
          >
            <span>Back to top</span>
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              width="12"
              height="12"
            >
              <path d="M8 13V3M3 8l5-5 5 5" />
            </svg>
          </button>
        </div>
      </footer>
    </div>
  );
}
