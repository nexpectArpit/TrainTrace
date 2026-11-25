import React from "react";
import { architectures, Field, Select } from "../../components/Common";

export default function CompareFilters({ workspace }) {
  const {
    setQuery,
    runs,
    compare,
    visibleRuns,
    archFilter,
    setArchFilter,
    statusFilter,
    setStatusFilter,
    seedFilter,
    setSeedFilter,
    validationMin,
    setValidationMin,
    validationMax,
    setValidationMax,
    datasetFilter,
    setDatasetFilter,
    optimizerFilter,
    setOptimizerFilter,
    depthFilter,
    setDepthFilter,
  } = workspace;
  const validationRangeInvalid =
    validationMin !== "" &&
    validationMax !== "" &&
    Number(validationMin) > Number(validationMax);
  const activeFilterCount = [
    archFilter,
    statusFilter,
    datasetFilter,
    optimizerFilter,
    seedFilter,
    depthFilter,
    validationMin,
    validationMax,
  ].filter((value) => value !== "").length;
  return (
    <>
      <details className="compare-filter-panel">
        <summary>
          Filters{activeFilterCount ? ` · ${activeFilterCount} active` : ""}
        </summary>
        <div className="compare-filter-toolbar">
          <Select
            label="Architecture"
            value={archFilter}
            onChange={setArchFilter}
          >
            <option value="">All architectures</option>
            {architectures.map((a) => (
              <option key={a} value={a}>
                {
                  {
                    custom_cnn: "Custom CNN",
                    resnet18: "ResNet-18",
                    mobilenet_v2: "MobileNetV2",
                    efficientnet_b0: "EfficientNet-B0",
                  }[a]
                }
              </option>
            ))}
          </Select>
          <Select
            label="Execution status"
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <option value="">All statuses</option>
            {[
              "QUEUED",
              "RUNNING",
              "COMPLETED",
              "FAILED",
              "STOPPED",
              "SELECTED",
              "REJECTED",
              "SUPERSEDED",
              "ACCEPTED",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </Select>
          <Select
            label="Dataset"
            value={datasetFilter}
            onChange={setDatasetFilter}
          >
            <option value="">All datasets</option>
            <option value="cifar10">CIFAR-10</option>
            <option value="cifar100">CIFAR-100</option>
            <option value="mnist">MNIST</option>
            <option value="fashion_mnist">Fashion-MNIST</option>
            <option value="svhn">SVHN</option>
          </Select>
          <Select
            label="Optimizer"
            value={optimizerFilter}
            onChange={setOptimizerFilter}
          >
            <option value="">All optimizers</option>
            <option value="adamw">AdamW</option>
            <option value="sgd">SGD</option>
          </Select>
        </div>
        <div className="compare-advanced-filters">
          <h3>More filters</h3>
          <div className="grid four">
            <Field
              label="Run seed"
              type="number"
              min="0"
              max="4294967295"
              value={seedFilter}
              onChange={(v) => setSeedFilter(v === null ? "" : String(v))}
            />
            <Select
              label="CustomCNN depth"
              value={depthFilter}
              onChange={setDepthFilter}
            >
              <option value="">All depths</option>
              {[2, 3, 4, 5, 6].map((depth) => (
                <option key={depth} value={depth}>
                  {depth} blocks
                </option>
              ))}
            </Select>
            <Field
              label="Min validation accuracy (%)"
              type="number"
              min="0"
              max="100"
              step="any"
              value={validationMin}
              aria-invalid={validationRangeInvalid}
              onChange={(v) => setValidationMin(v === null ? "" : String(v))}
            />
            <Field
              label="Max validation accuracy (%)"
              type="number"
              min="0"
              max="100"
              step="any"
              value={validationMax}
              aria-invalid={validationRangeInvalid}
              onChange={(v) => setValidationMax(v === null ? "" : String(v))}
            />
          </div>
          {validationRangeInvalid && (
            <p className="queue-disabled-reason" role="status">
              Minimum validation accuracy cannot be higher than maximum
              validation accuracy.
            </p>
          )}
        </div>
      </details>
      <div className="compare-results-meta">
        <p role="status">
          Showing {visibleRuns.length} of {runs.length} runs · {compare.length}{" "}
          selected (up to 4)
        </p>
        <button
          type="button"
          className="link"
          onClick={() => {
            setQuery("");
            setArchFilter("");
            setStatusFilter("");
            setSeedFilter("");
            setDatasetFilter("");
            setOptimizerFilter("");
            setDepthFilter("");
            setValidationMin("");
            setValidationMax("");
          }}
        >
          Clear filters
        </button>
      </div>
    </>
  );
}
