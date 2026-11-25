import React from "react";
import { formatTime } from "../components/Common";
import { request } from "../services/api";
import Inference from "./Inference";
import {
  fmt,
  Badge,
  Field,
  Panel,
  Json,
  RequiredFieldLegend,
  TagsField,
} from "../components/Common";

const releaseNamePattern = /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/;
const semanticVersionPattern =
  /^v?(0|[1-9][0-9]*)[.](0|[1-9][0-9]*)[.](0|[1-9][0-9]*)$/;

export default function Registry({ workspace }) {
  const {
    models,
    activeModel,
    online,
    setNotice,
    busy,
    query,
    decision,
    release,
    setRelease,
    lineage,
    setLineage,
    lineageId,
    setLineageId,
    setPrediction,
    run,
    setRunId,
    act,
    loadLineage,
  } = workspace;
  const visibleModels = models.filter(
    (model) =>
      !query ||
      `${model.name} ${model.run_id} ${model.version}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const registerDisabledReason = !online
    ? "Connect to the backend before registering a model."
    : !run
      ? "Choose a candidate run to register."
      : run.status !== "COMPLETED"
        ? "The selected run must complete before registration."
        : run.final_evaluation_status === "HISTORICAL"
          ? "Historical test metrics were exposed during selection; this run cannot be registered as a final candidate."
          : run.final_evaluation_status !== "COMPLETED"
            ? "Run the selected candidate's final test evaluation from Decisions first."
            : run.latest_decision?.status !== "SELECTED"
              ? "Select this candidate in Decisions before registering it."
              : !run.config
                ? "This run has no captured configuration and cannot be verified."
                : !releaseNamePattern.test(release.name || "")
                  ? "Release name: use 1–80 letters, numbers, hyphens or underscores; no spaces. Example: mnist-resnet18."
                  : !semanticVersionPattern.test(release.version || "")
                    ? "Semantic version: use three numbers, such as v1.0.0 or 1.0.0."
                    : "";
  const lineageRuns = lineage?.investigation_history || [];
  const orderedModels = [...visibleModels].sort(
    (a, b) => Number(b.id === activeModel) - Number(a.id === activeModel),
  );
  return (
    <>
      <Panel title="Registered model versions">
        <p className="panel-intro">
          Each row is an immutable release. Activate a verified version before
          using the serving panel below.
        </p>
        {orderedModels.length ? (
          <>
            <p className="table-scroll-hint">
              Scroll horizontally for release evidence and actions →
            </p>
            <div
              className="table-wrap table-scroll"
              role="region"
              aria-label="Registered model versions; scroll horizontally for all columns"
              tabIndex={0}
            >
              <table className="registry-model-table">
                <caption>Registered models and release status</caption>
                <thead>
                  <tr>
                    <th scope="col">Model release</th>
                    <th scope="col">Source run</th>
                    <th scope="col">Dataset</th>
                    <th scope="col">Decision</th>
                    <th scope="col">Holdout accuracy</th>
                    <th scope="col">Registered</th>
                    <th scope="col">State</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orderedModels.map((model) => (
                    <tr key={model.id}>
                      <td>
                        <strong>
                          {model.name}:{model.version}
                        </strong>
                      </td>
                      <td>
                        <span title={model.run_id}>
                          {model.source_approach ||
                            (lineageId === model.id
                              ? lineage?.originating_run?.approach_name
                              : null) ||
                            model.run_id}
                        </span>
                      </td>
                      <td>
                        {model.dataset_name ||
                          (lineageId === model.id
                            ? lineage?.configuration?.dataset_name
                            : null) ||
                          "Unknown"}
                      </td>
                      <td>
                        {model.decision_status ||
                          (lineageId === model.id
                            ? lineage?.decision?.status
                            : null) ||
                          "Unknown"}
                      </td>
                      <td>
                        {model.test_accuracy == null
                          ? "Not measured"
                          : `${fmt(model.test_accuracy)}%`}
                      </td>
                      <td>{formatTime(model.created_at)}</td>
                      <td>
                        <Badge
                          value={
                            activeModel === model.id
                              ? "ACTIVE"
                              : model.sha256
                                ? "VERIFIED"
                                : "LEGACY UNVERIFIED"
                          }
                        />
                      </td>
                      <td>
                        <div className="registry-row-actions">
                          <button
                            disabled={busy || !online}
                            onClick={() => loadLineage(model.id)}
                          >
                            Lineage
                          </button>
                          <button
                            disabled={
                              busy ||
                              !model.sha256 ||
                              !online ||
                              activeModel === model.id
                            }
                            onClick={() =>
                              act(async () => {
                                await request(
                                  `/registry/${model.id}/activate`,
                                  "POST",
                                );
                                setPrediction(null);
                                setNotice(
                                  "Registered version activated for inference.",
                                );
                              })
                            }
                          >
                            {activeModel === model.id ? "Active" : "Activate"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="empty">
            {models.length
              ? "No registered versions match this search."
              : "No registered versions yet. Select a completed candidate to create the first release."}
          </div>
        )}
      </Panel>
      <details className="model-registration-disclosure">
        <summary>Register a selected candidate as a release</summary>
        <Panel title="Register selected candidate">
          <p>
            Registration freezes the evaluated weights, decision and
            investigation history. Names and semantic versions are immutable.
            Activation for inference is a separate step.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                const result = await request("/registry/register", "POST", {
                  ...release,
                  run_id: run.id,
                });
                setNotice(
                  `Registered ${result.model.name}:${result.model.version}`,
                );
                setLineageId(result.model.id);
                setLineage(
                  await request(`/registry/${result.model.id}/lineage`),
                );
              });
            }}
          >
            <RequiredFieldLegend />
            <div className="grid two">
              <Field
                label="Release name"
                info="Use 1–80 letters, numbers, hyphens or underscores. Start with a letter or number; spaces are not allowed. Example: cifar10-demo3."
                pattern="[A-Za-z0-9][A-Za-z0-9_-]{0,79}"
                placeholder="e.g. cifar10-demo3"
                title="Use letters, numbers, hyphens or underscores without spaces (maximum 80 characters)."
                value={release.name}
                onChange={(v) => setRelease({ ...release, name: v })}
                required
              />
              <Field
                label="Semantic version"
                info="Use three dot-separated nonnegative numbers, optionally prefixed with v. Example: v1.0.0."
                value={release.version}
                onChange={(v) => setRelease({ ...release, version: v })}
                placeholder="e.g. 1.0.0"
                pattern="v?(0|[1-9][0-9]*)[.](0|[1-9][0-9]*)[.](0|[1-9][0-9]*)"
                title="Use a semantic version such as v1.0.0 or 1.0.0."
                required
              />
            </div>
            <TagsField
              value={release.tags}
              onChange={(tags) => setRelease({ ...release, tags })}
            />
            <button
              className="primary"
              disabled={busy || !!registerDisabledReason}
            >
              {busy ? "Registering…" : "Register selected candidate"}
            </button>
            {registerDisabledReason && (
              <p className="queue-disabled-reason" role="status">
                {registerDisabledReason}
              </p>
            )}
          </form>
        </Panel>
      </details>
      {lineage && (
        <Panel title={`Frozen lineage · ${lineageId}`}>
          <p>
            {lineage.verified
              ? "Provenance snapshot recorded at registration. Inspect evidence and missing fields below."
              : lineage.reason}
          </p>
          {lineage.verified && (
            <>
              <p>
                <strong>Objective:</strong>{" "}
                {lineage.source_experiment.objective}
              </p>
              <p>
                <strong>Selection:</strong> {lineage.decision.rationale}
              </p>
              <h3>Investigation sequence</h3>
              <p>
                Open a source run to inspect its saved metrics and
                configuration. The predecessor field records the research link,
                not inherited weights.
              </p>
              {lineage.investigation_history.map((r) => (
                <article className="record" key={r.id}>
                  <h3>{r.approach_name}</h3>
                  <p>
                    Predecessor:{" "}
                    {lineageRuns.find(
                      (candidate) => candidate.id === r.predecessor_run_id,
                    )?.approach_name ||
                      (r.predecessor_run_id
                        ? "Outside this snapshot"
                        : "Initial approach")}{" "}
                    · {r.motivating_reason || "No motivation recorded"}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setRunId(r.id);
                      workspace.setTab("Training");
                    }}
                  >
                    Open source run
                  </button>
                  {r.decisions.map((d) => (
                    <p key={d.id}>
                      {d.status}: {d.rationale}
                    </p>
                  ))}
                </article>
              ))}
            </>
          )}
          <Json data={lineage} label="Full immutable registry manifest" />
        </Panel>
      )}
      <Inference workspace={workspace} mode="serving" />
    </>
  );
}
