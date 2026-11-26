import { DEFAULT_ARCHITECTURE_CONFIG } from "../../components/Common";

export const architectureLabels = {
  custom_cnn: "Custom CNN (configurable)",
  resnet18: "ResNet-18 — residual CNN",
  mobilenet_v2: "MobileNetV2 — mobile-optimized",
  efficientnet_b0: "EfficientNet-B0 — compound-scaled CNN",
};

export const architectureFields = [
  [
    "depth",
    "Convolution blocks",
    2,
    6,
    1,
    "Number of convolutional feature blocks. More blocks increase network depth and compute.",
  ],
  [
    "width",
    "Starting channels",
    8,
    128,
    1,
    "Channel count in the first block. Later blocks expand from this starting width.",
  ],
  [
    "classifier_width",
    "Classifier units",
    16,
    2048,
    16,
    "Hidden units in the classifier head before the output classes (multiples of 16).",
  ],
  [
    "dropout",
    "Dropout",
    0,
    1 - Number.EPSILON / 2,
    "any",
    "Fraction of classifier activations randomly dropped during training to reduce overfitting.",
    "Allowed: 0 ≤ value < 1",
  ],
];

export const trainingFields = [
  [
    "epochs",
    "Epochs",
    1,
    1000,
    1,
    "Number of complete passes over the training split. More epochs increase training time.",
  ],
  [
    "batch_size",
    "Batch size",
    2,
    2048,
    1,
    "Examples processed together for each optimizer update. Larger batches use more memory; lower this if training runs out of memory.",
  ],
  [
    "learning_rate",
    "Learning rate",
    Number.MIN_VALUE,
    1,
    "any",
    "Step size used by the optimizer when updating model weights. This is a key training parameter.",
    "Allowed: greater than 0 and at most 1",
  ],
  [
    "seed",
    "Run randomness seed",
    0,
    4294967295,
    1,
    "Controls model initialization (unless ImageNet weights are used), training data order, and other seeded randomness. Keep it fixed to reproduce a run.",
  ],
  [
    "split_seed",
    "Dataset split seed",
    0,
    4294967295,
    1,
    "Controls which training examples go to the training and validation splits. Keep it fixed when comparing approaches so they use the same split.",
  ],
  [
    "weight_decay",
    "Weight decay",
    0,
    1,
    "any",
    "Regularization strength that discourages overly large weights. AdamW applies decoupled weight decay; SGD applies optimizer weight decay.",
  ],
];

export function isNumberInRange(value, min, max, step = 1) {
  if (value === null || value === undefined || value === "") return false;
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || number > max) return false;
  if (step === "any") return true;
  const increments = (number - min) / Number(step);
  return Math.abs(increments - Math.round(increments)) < 1e-7;
}

export function validateRunConfiguration(setup) {
  const architectureValuesValid =
    setup.model_name === "custom_cnn"
      ? architectureFields.every(([key, , min, max, step]) =>
          isNumberInRange(setup.architecture_config?.[key], min, max, step),
        )
      : Object.entries(DEFAULT_ARCHITECTURE_CONFIG).every(
          ([key, value]) => setup.architecture_config?.[key] === value,
        );
  const trainingValuesValid = trainingFields.every(([key, , min, max, step]) =>
    isNumberInRange(setup[key], min, max, step),
  );
  const requiredRunFieldsValid = Boolean(
    String(setup.approach_name ?? "").trim() &&
    /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(setup.run_id ?? "") &&
    (!setup.predecessor_run_id || String(setup.motivating_reason ?? "").trim()),
  );
  const trainingConfigValid =
    requiredRunFieldsValid && architectureValuesValid && trainingValuesValid;
  const invalidFields = [
    ...(!String(setup.approach_name ?? "").trim() ? ["approach name"] : []),
    ...(!/^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(setup.run_id ?? "")
      ? ["generated run ID"]
      : []),
    ...trainingFields
      .filter(
        ([key, , min, max, step]) =>
          !isNumberInRange(setup[key], min, max, step),
      )
      .map(([, label]) => label.toLowerCase()),
    ...(setup.model_name === "custom_cnn"
      ? architectureFields
          .filter(
            ([key, , min, max, step]) =>
              !isNumberInRange(
                setup.architecture_config?.[key],
                min,
                max,
                step,
              ),
          )
          .map(([, label]) => label.toLowerCase())
      : !architectureValuesValid
        ? ["architecture configuration"]
        : []),
    ...(setup.predecessor_run_id &&
    !String(setup.motivating_reason ?? "").trim()
      ? ["reason for continuing from a prior run"]
      : []),
  ];
  const advancedInvalid = invalidFields.some((label) =>
    [
      "dataset split seed",
      "weight decay",
      "reason for continuing from a prior run",
    ].includes(label),
  );
  return { trainingConfigValid, invalidFields, advancedInvalid };
}
