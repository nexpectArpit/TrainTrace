export const stages = [
  {
    title: "Configure",
    label: "A controlled experiment starts here.",
    text: "Choose a dataset, architecture, optimizer, batch size, learning rate, seed, and schedule. For CustomCNN, control depth, width, classifier size, and dropout.",
    rows: [
      ["Dataset", "MNIST"],
      ["Architecture", "ResNet-18"],
      ["Optimizer", "AdamW"],
      ["Split seed", "42 (recorded with the run)"],
    ],
  },
  {
    title: "Observe",
    label: "See the process behind the score.",
    text: "Follow sampled batch loss, running accuracy, throughput, and available device measurements. Inspect completed epoch metrics and adjust chart smoothing, axis, and visibility.",
    rows: [
      ["Batch signals", "Loss, accuracy, throughput"],
      ["Epoch signals", "Train / validation curves"],
      ["System signals", "Available CPU and GPU measurements"],
      ["Chart controls", "Expand, smooth, export CSV"],
    ],
  },
  {
    title: "Compare",
    label: "Understand what changed—and why.",
    text: "Compare run configurations and validation curves. Look at quality alongside runtime and checkpoint size before choosing your next experiment.",
    rows: [
      ["Run A", "ResNet-18"],
      ["Run B", "MobileNetV2"],
      ["Same split", "Compare recorded split identity"],
      ["Trade-offs", "Quality, duration, model size"],
    ],
  },
  {
    title: "Decide",
    label: "Carry the evidence into the next step.",
    text: "Record your rationale, reserve a candidate for final evaluation, register a checkpoint, and compare model predictions on an uploaded image.",
    rows: [
      ["Decision", "Rationale and accepted trade-offs"],
      ["Final evaluation", "Separate test partition"],
      ["Registry", "Versioned checkpoint records"],
      ["Inference", "Predictions and confidence"],
    ],
  },
];
export const capabilities = [
  [
    "Investigations & lineage",
    "Keep objectives, hypotheses, predecessor runs, and decisions connected so the next experiment has context.",
  ],
  [
    "Five image datasets",
    "CIFAR-10, CIFAR-100, MNIST, Fashion-MNIST, and SVHN, with dataset-specific transforms and recorded splits.",
  ],
  [
    "Four model families",
    "CustomCNN, ResNet-18, MobileNetV2, and EfficientNet-B0. Choose supported ImageNet initialization where appropriate.",
  ],
  [
    "Live charts & exports",
    "Inspect batch and epoch signals, change chart settings, expand a view, and download the underlying readings as CSV.",
  ],
  [
    "Reproducibility audits",
    "Inspect repeat-run trajectories and seed variability. Recorded environments and split identities help explain differences.",
  ],
  [
    "Final evaluation reports",
    "Inspect held-out results, class-level metrics, and confusion-matrix artifacts after selecting a candidate.",
  ],
  [
    "Registry & image inference",
    "Keep model versions attached to their runs. Upload an image and compare checkpoint predictions and confidence.",
  ],
  [
    "Notebook & artifact access",
    "Export a configured notebook and inspect readable metrics, configuration, dataset splits, reports, and saved checkpoints.",
  ],
  [
    "Search & research history",
    "Find runs using recorded names, tags, configurations, and filters. Revisit the evidence behind earlier decisions.",
  ],
];
