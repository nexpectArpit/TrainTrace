import React, { useState } from "react";
import { request } from "../services/api";
import { Field, Select, Panel, Badge } from "../components/Common";

export default function Search({ workspace }) {
  const { act, busy, switchExperiment, setRunId, setTab, loadLineage } =
    workspace;
  const [filters, setFilters] = useState({
    tag_key: "",
    tag_value: "",
    search: "",
    dataset_name: "",
    architecture: "",
    status: "",
    seed: "",
    accuracy_min: "",
    accuracy_max: "",
  });
  const [results, setResults] = useState(null);
  const [searchOffset, setSearchOffset] = useState(0);
  const accuracyRangeInvalid =
    filters.accuracy_min !== "" &&
    filters.accuracy_max !== "" &&
    Number(filters.accuracy_min) > Number(filters.accuracy_max);
  const tagPairInvalid =
    Boolean(filters.tag_key) !== Boolean(filters.tag_value);
  const tagKeyInvalid =
    Boolean(filters.tag_key) &&
    !/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/.test(filters.tag_key);
  const numericInvalid = [filters.accuracy_min, filters.accuracy_max].some(
    (value) =>
      value !== "" &&
      (!Number.isFinite(Number(value)) ||
        Number(value) < 0 ||
        Number(value) > 100),
  );
  const runSearch = async (offset = 0, append = false) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "") params.set(key, value);
    });
    params.set("offset", String(offset));
    params.set("limit", "50");
    const page = await request(`/runs/search?${params.toString()}`);
    setResults((current) =>
      append && current
        ? {
            ...page,
            runs: [...current.runs, ...page.runs],
            experiments: [...current.experiments, ...page.experiments],
            models: [...current.models, ...page.models],
          }
        : page,
    );
    setSearchOffset(offset);
  };
  return (
    <Panel title="Global search">
      <p>
        Search investigations, runs, and registered releases. Open a result to
        continue its workflow.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          act(() => runSearch(0, false));
        }}
      >
        <div className="grid">
          <Field
            label="Text"
            maxLength="256"
            value={filters.search}
            onChange={(v) => setFilters({ ...filters, search: v })}
            placeholder="e.g. run ID or resnet18"
          />
        </div>
        <details className="search-advanced-filters">
          <summary>Advanced filters</summary>
          <p>
            Final test accuracy applies only to selected runs whose holdout
            evaluation completed after selection.
          </p>
          <div className="grid three">
            <Field
              label="Tag key"
              maxLength="64"
              aria-invalid={tagKeyInvalid}
              value={filters.tag_key}
              onChange={(v) => setFilters({ ...filters, tag_key: v })}
              placeholder="e.g. dataset"
            />
            <Field
              label="Tag value"
              maxLength="256"
              value={filters.tag_value}
              onChange={(v) => setFilters({ ...filters, tag_value: v })}
              placeholder="e.g. cifar100"
            />
            <Select
              label="Dataset"
              value={filters.dataset_name}
              onChange={(v) => setFilters({ ...filters, dataset_name: v })}
            >
              <option value="">All datasets</option>
              {["cifar10", "cifar100", "mnist", "fashion_mnist", "svhn"].map(
                (name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ),
              )}
            </Select>
            <Select
              label="Architecture"
              value={filters.architecture}
              onChange={(v) => setFilters({ ...filters, architecture: v })}
            >
              <option value="">All architectures</option>
              {[
                "custom_cnn",
                "resnet18",
                "mobilenet_v2",
                "efficientnet_b0",
              ].map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Select>
            <Select
              label="Run or decision status"
              value={filters.status}
              onChange={(v) => setFilters({ ...filters, status: v })}
            >
              <option value="">Any status</option>
              {[
                "QUEUED",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "STOPPED",
                "SELECTED",
                "REJECTED",
                "SUPERSEDED",
              ].map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
            <Field
              label="Seed"
              type="number"
              min="0"
              max="4294967295"
              value={filters.seed}
              onChange={(v) =>
                setFilters({ ...filters, seed: v === null ? "" : String(v) })
              }
            />
            <Field
              label="Min final test accuracy (%)"
              type="number"
              min="0"
              max="100"
              step="any"
              aria-invalid={accuracyRangeInvalid}
              value={filters.accuracy_min}
              onChange={(v) =>
                setFilters({
                  ...filters,
                  accuracy_min: v === null ? "" : String(v),
                })
              }
            />
            <Field
              label="Max final test accuracy (%)"
              type="number"
              min="0"
              max="100"
              step="any"
              aria-invalid={accuracyRangeInvalid}
              value={filters.accuracy_max}
              onChange={(v) =>
                setFilters({
                  ...filters,
                  accuracy_max: v === null ? "" : String(v),
                })
              }
            />
          </div>
        </details>
        <button
          className="primary"
          disabled={
            busy ||
            tagPairInvalid ||
            tagKeyInvalid ||
            accuracyRangeInvalid ||
            numericInvalid
          }
        >
          Search records
        </button>
        {tagPairInvalid && (
          <p className="queue-disabled-reason" role="status">
            Enter both a tag key and tag value, or leave both empty.
          </p>
        )}
        {tagKeyInvalid && (
          <p className="queue-disabled-reason" role="status">
            Tag keys must start with a letter and contain only letters, numbers,
            underscores, dots or hyphens (maximum 64 characters).
          </p>
        )}
        {numericInvalid && (
          <p className="queue-disabled-reason" role="status">
            Accuracy limits must be between 0 and 100 percent.
          </p>
        )}
        {accuracyRangeInvalid && (
          <p className="queue-disabled-reason" role="status">
            Minimum accuracy cannot be higher than maximum accuracy.
          </p>
        )}
      </form>
      {results && (
        <section className="global-search-results" aria-live="polite">
          <h2>
            Results{" "}
            {results.tag && `for ${results.tag.key}=${results.tag.value}`}
          </h2>
          <h3>Investigations · {results.experiments.length}</h3>
          {results.experiments.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                switchExperiment(item.id);
                setTab("Investigations");
              }}
            >
              {item.name} · {item.id}
            </button>
          ))}
          <h3>Runs · {results.runs.length}</h3>
          {results.runs.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                switchExperiment(item.experiment_id);
                setRunId(item.id);
                setTab("Training");
              }}
            >
              {item.approach_name} · {item.model_architecture} · seed{" "}
              {item.seed} <Badge value={item.status} />
            </button>
          ))}
          <h3>Models · {results.models.length}</h3>
          {results.models.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setTab("Registry");
                loadLineage(item.id);
              }}
            >
              {item.name}:{item.version} ·{" "}
              {item.test_accuracy ?? "no test metric"}
            </button>
          ))}
          {!results.runs.length &&
            !results.experiments.length &&
            !results.models.length && (
              <p className="empty">
                No records match these filters. Try a broader text search or
                clear an advanced filter.
              </p>
            )}
          {(results.runs.length === results.limit ||
            results.experiments.length === results.limit ||
            results.models.length === results.limit) && (
            <button
              disabled={busy}
              onClick={() =>
                act(() => runSearch(searchOffset + results.limit, true))
              }
            >
              Load next page
            </button>
          )}
        </section>
      )}
    </Panel>
  );
}
