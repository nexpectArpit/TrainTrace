import AdvancedRunSettings from "./AdvancedRunSettings";
import React from "react";
import InfoTooltip from "../../components/InfoTooltip";
import {
  architectures,
  DEFAULT_ARCHITECTURE_CONFIG,
  Field,
  Select,
} from "../../components/Common";
import {
  architectureLabels,
  architectureFields,
  trainingFields,
  isNumberInRange,
} from "./runFormSchema";

const RUN_PRESETS = [
  {
    label: "Quick 2-epoch test",
    epochs: 2,
    batch_size: 128,
    learning_rate: 0.001,
  },
  {
    label: "Standard 5 epochs",
    epochs: 5,
    batch_size: 128,
    learning_rate: 0.001,
  },
  {
    label: "Full 15 epochs",
    epochs: 15,
    batch_size: 64,
    learning_rate: 0.0005,
  },
];

export default function RunSetupFields({
  setup,
  setSetup,
  runs,
  advancedInvalid,
}) {
  return (
    <>
      <div className="run-preset-bar" role="group" aria-label="Quick presets">
        <span className="run-preset-label">Presets:</span>
        {RUN_PRESETS.map((preset) => {
          const isActive =
            Number(setup.epochs) === preset.epochs &&
            Number(setup.batch_size) === preset.batch_size &&
            Number(setup.learning_rate) === preset.learning_rate;
          return (
            <button
              key={preset.label}
              type="button"
              className={`run-preset-chip${isActive ? " is-active" : ""}`}
              onClick={() =>
                setSetup({
                  ...setup,
                  epochs: preset.epochs,
                  batch_size: preset.batch_size,
                  learning_rate: preset.learning_rate,
                })
              }
            >
              {preset.label}
            </button>
          );
        })}
      </div>
      <div className="grid-identity">
        <Field
          label="Approach name"
          info="A short human-readable name that distinguishes this run in comparisons and history. Include the main change you are investigating."
          value={setup.approach_name}
          onChange={(v) => setSetup({ ...setup, approach_name: v })}
          placeholder="e.g. Wider CNN with cosine schedule"
          required
        />
        <Field
          label="Run ID"
          value={setup.run_id}
          info="Generated automatically. Links this run to its metrics, checkpoints, and history; edit only when you need a specific ID."
          pattern="[A-Za-z0-9][A-Za-z0-9_-]{0,79}"
          onChange={(v) => setSetup({ ...setup, run_id: v })}
          required
        />
      </div>
      <div className="grid three">
        <Select
          label="Dataset"
          info="Selects the dataset and class count used for training and validation. CIFAR-100 is available as a separate 100-class dataset."
          value={setup.dataset_name}
          onChange={(v) => setSetup({ ...setup, dataset_name: v })}
          required
        >
          <option value="cifar10">CIFAR-10 · 10 classes</option>
          <option value="cifar100">CIFAR-100 · 100 classes</option>
          <option value="mnist">MNIST · 10 classes</option>
          <option value="fashion_mnist">Fashion-MNIST · 10 classes</option>
          <option value="svhn">SVHN · 10 classes</option>
        </Select>
        <Select
          label="Architecture"
          info={
            setup.model_name === "custom_cnn"
              ? "Custom CNN exposes depth, channel width, classifier width, and dropout below. The preset architectures use fixed layer layouts."
              : "Preset architecture with a fixed layer layout. Select Custom CNN if you need direct control over depth and width."
          }
          value={setup.model_name}
          onChange={(v) =>
            setSetup({
              ...setup,
              model_name: v,
              pretrained: v === "custom_cnn" ? false : setup.pretrained,
              architecture_config:
                v === "custom_cnn"
                  ? setup.architecture_config
                  : { ...DEFAULT_ARCHITECTURE_CONFIG },
            })
          }
          required
        >
          {architectures.map((a) => (
            <option key={a} value={a}>
              {architectureLabels[a]}
            </option>
          ))}
        </Select>
        <Select
          label="Optimizer"
          info={
            setup.optimizer === "sgd"
              ? "SGD uses momentum fixed at 0.9 in this version."
              : "AdamW uses PyTorch's default beta values. Weight decay is configured separately below."
          }
          value={setup.optimizer}
          onChange={(v) => setSetup({ ...setup, optimizer: v })}
          required
        >
          <option value="adamw">AdamW</option>
          <option value="sgd">SGD (momentum 0.9)</option>
        </Select>
      </div>
      {setup.model_name === "custom_cnn" && (
        <fieldset className="architecture-controls-flat">
          <legend>
            Custom CNN architecture
            <InfoTooltip label="About Custom CNN settings">
              Set convolution block depth, starting channel width, classifier
              hidden units, and dropout. Later feature blocks grow in width. The
              full architecture profile is saved with the run and checkpoint.
            </InfoTooltip>
          </legend>
          <div className="grid four">
            {architectureFields.map(
              ([key, label, min, max, step, info, rangeLabel]) => (
                <Field
                  key={key}
                  label={label}
                  info={info}
                  type="number"
                  min={min}
                  max={max}
                  step={step}
                  rangeLabel={rangeLabel}
                  aria-invalid={
                    !isNumberInRange(
                      setup.architecture_config?.[key],
                      min,
                      max,
                      step,
                    )
                  }
                  value={setup.architecture_config[key]}
                  onChange={(value) =>
                    setSetup({
                      ...setup,
                      architecture_config: {
                        ...setup.architecture_config,
                        [key]: value,
                      },
                    })
                  }
                  required
                />
              ),
            )}
          </div>
        </fieldset>
      )}
      <div className="grid four">
        {trainingFields
          .filter(([key]) =>
            ["epochs", "batch_size", "learning_rate", "seed"].includes(key),
          )
          .map(([k, l, min, max, step, info, rangeLabel]) => (
            <Field
              key={k}
              label={l}
              info={info}
              type="number"
              step={step}
              min={min}
              max={max}
              rangeLabel={rangeLabel}
              aria-invalid={!isNumberInRange(setup[k], min, max, step)}
              required
              value={setup[k]}
              onChange={(v) => setSetup({ ...setup, [k]: v })}
            />
          ))}
      </div>
      {setup.model_name === "custom_cnn" ? (
        <div className="initialization-note">
          <strong>
            Custom CNN trains from scratch.
            <InfoTooltip label="About model initialization">
              ImageNet initialization is supported only for the preset
              architectures. Custom CNN starts with randomly initialized
              weights.
            </InfoTooltip>
          </strong>
        </div>
      ) : (
        <label className="check pretrained-check">
          <input
            type="checkbox"
            checked={setup.pretrained}
            onChange={(e) =>
              setSetup({ ...setup, pretrained: e.target.checked })
            }
          />
          <span>Initialize with ImageNet weights</span>
          <InfoTooltip label="About ImageNet initialization">
            The preset model starts from weights learned on ImageNet, then
            fine-tunes on the selected dataset. The first use downloads the
            weights.
          </InfoTooltip>
        </label>
      )}
      <AdvancedRunSettings
        setup={setup}
        setSetup={setSetup}
        runs={runs}
        advancedInvalid={advancedInvalid}
      />
    </>
  );
}
