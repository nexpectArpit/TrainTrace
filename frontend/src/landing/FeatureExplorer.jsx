import React, { useState } from "react";
import "./feature-explorer.css";
import Reveal from "./Reveal";

const groups = [
  {
    name: "Experiment control",
    intro: "Make the configuration part of the evidence.",
    items: [
      [
        "Architecture controls",
        "CustomCNN depth, channel width, classifier width, and dropout; ResNet-18, MobileNetV2, and EfficientNet-B0 alternatives.",
      ],
      [
        "Training controls",
        "Epoch count, batch size, learning rate, AdamW or SGD, weight decay, and constant, cosine, or step scheduling.",
      ],
      [
        "Initialization & iteration",
        "Optional ImageNet weights for supported models, predecessor context, and compatible local checkpoint warm starts.",
      ],
      [
        "Data & randomness",
        "Five dataset choices, separate run and split seeds, recorded transforms, and fixed train/validation partition identities.",
      ],
    ],
  },
  {
    name: "Live understanding",
    intro: "Look at learning and compute together.",
    items: [
      [
        "Learning signals",
        "Sampled batch loss and running accuracy; per-epoch training and validation loss, accuracy, learning rate, and duration.",
      ],
      [
        "Compute signals",
        "Throughput, allocated device memory, CPU and worker memory; available Kaggle GPU utilization, VRAM, temperature, and power readings.",
      ],
      [
        "Chart exploration",
        "Step and epoch axes, smoothing, log scale, chart search, visibility, rearrangement, expanded charts, and pause/resume views.",
      ],
      [
        "Progress & export",
        "Preparation and execution stages, batch progress, recorded-epoch time estimates, event history, and downloadable metric CSVs.",
      ],
    ],
  },
  {
    name: "Scientific decisions",
    intro: "Choose a candidate with the context attached.",
    items: [
      [
        "Run comparisons",
        "Overlay validation trajectories, inspect configurations and differences, and filter candidates by dataset, architecture, optimizer, seed, or score.",
      ],
      [
        "Reproducibility",
        "Protocol A compares repeated trajectories and state hashes; Protocol B explores seed variability and descriptive confidence intervals.",
      ],
      [
        "Decision records",
        "Save rationale, limitations, accepted trade-offs, and next investigations alongside the evidence used for selection.",
      ],
      [
        "Final test boundary",
        "Reserve a candidate before final evaluation. Keep final test evidence separate from validation used during training.",
      ],
    ],
  },
  {
    name: "Models & evidence",
    intro: "Keep every result connected to its source.",
    items: [
      [
        "Checkpoint provenance",
        "Best and last checkpoints, checksum records, configuration snapshots, dataset split identity, and environment/source metadata.",
      ],
      [
        "Versioned registry",
        "Register a model version with its checkpoint and frozen research lineage; select an active version for inference.",
      ],
      [
        "Image predictions",
        "Compare completed checkpoints on one upload; inspect class confidence, inference latency, and optional correct-label matches.",
      ],
      [
        "Readable analysis",
        "Run metrics CSVs, evaluation reports, confusion matrices, image previews, analysis notebooks, and exported training notebooks.",
      ],
    ],
  },
];
export default function FeatureExplorer() {
  const [active, setActive] = useState(0);
  const group = groups[active];
  return (
    <Reveal as="section" className="tt-feature-explorer" id="feature-details">
      <div className="tt-kicker">EXPLORE THE DETAILS</div>
      <h2>
        More control.
        <br />
        More context for every result.
      </h2>
      <div className="tt-feature-browser">
        <div
          className="tt-feature-menu"
          role="group"
          aria-label="Feature category"
        >
          {groups.map((item, i) => (
            <button
              key={item.name}
              aria-pressed={i === active}
              onClick={() => setActive(i)}
            >
              <span>0{i + 1}</span>
              {item.name}
              <svg
                className="tt-feature-arrow"
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
                <path d="M6 12l4-4-4-4" />
              </svg>
            </button>
          ))}
        </div>
        <div className="tt-feature-content" key={active}>
          <h3>{group.intro}</h3>
          <div>
            {group.items.map(([name, text]) => (
              <article key={name}>
                <span className="tt-feature-bullet" aria-hidden="true" />
                <div>
                  <h4>{name}</h4>
                  <p>{text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </Reveal>
  );
}
