const tabs = [
  "Investigations",
  "Training",
  "Compare",
  "Audits",
  "Decisions",
  "History",
  "Registry",
  "Inference",
  "Search",
];
const navGroups = [
  {
    label: "RESEARCH",
    items: ["Investigations", "Training", "Compare"],
  },
  { label: "OUTCOMES", items: ["Decisions", "Registry"] },
];
const tabLabels = {
  Training: "Runs",
  Registry: "Models",
  Audits: "Reproducibility",
  Inference: "Serving",
};
const tabIconPaths = {
  Investigations: "M12 3 3 8l9 5 9-5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5",
  Training: "M8 5v14l11-7-11-7Z",
  Compare: "M4 7h14m0 0-4-4m4 4-4 4M20 17H6m0 0 4-4m-4 4 4 4",
  Audits: "m5 12 4 4L19 6",
  Decisions:
    "M12 3l2.3 5.3L20 10l-4.3 3.8L17 20l-5-3-5 3 1.3-6.2L4 10l5.7-1.7L12 3Z",
  History: "M3 12a9 9 0 1 0 2.6-6.4L3 8m0-5v5h5m4-1v5l3 2",
  Registry: "M4 5h16v14H4zM8 9h8M8 13h8M8 17h4",
  Inference: "M4 12h4l3-8 5 16 3-8h3",
  Search: "m21 21-4.3-4.3M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z",
};
const tabDescriptions = {
  Investigations: "Define the question and keep its research history together.",
  Training: "Configure runs and inspect live training evidence.",
  Compare: "Compare model behavior, metrics, and recorded configurations.",
  Audits: "Review saved validation evidence and optional repeatability checks.",
  Decisions: "Record evidence-backed candidate decisions.",
  History: "Follow the reasoning and lineage across candidate runs.",
  Registry: "Manage immutable, versioned model releases.",
  Inference:
    "Compare verified checkpoints from completed runs side by side, or serve predictions with an activated registered version.",
  Search: "Find runs, investigations, and models by tags and metadata.",
};
const normalizeSearchText = (value) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");

export {
  tabs,
  navGroups,
  tabLabels,
  tabIconPaths,
  tabDescriptions,
  normalizeSearchText,
};
