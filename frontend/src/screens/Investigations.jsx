import React from "react";
import { request } from "../services/api";
import {
  activeStates,
  emptyExperiment,
  evidenceText,
  Field,
  Panel,
  RequiredFieldLegend,
  TagsField,
} from "../components/Common";
import InvestigationTimeline from "../components/InvestigationTimeline";

const editLabels = {
  name: "Investigation name",
  objective: "Objective",
  hypothesis: "Hypothesis",
  conclusion: "Conclusion",
};

export default function Investigations({ workspace }) {
  const {
    setTab,
    expId,
    experiments,
    query,
    setQuery,
    runs,
    online,
    setNotice,
    busy,
    newExp,
    setNewExp,
    editExp,
    setEditExp,
    experiment,
    act,
    switchExperiment,
    setRunId,
    branch,
  } = workspace;
  const filteredExperiments = experiments.filter(
    (item) =>
      !query ||
      `${item.name} ${item.id}`.toLowerCase().includes(query.toLowerCase()),
  );
  const completedRuns = runs.filter((run) => run.status === "COMPLETED").length;
  const activeRun = runs.find((run) => activeStates.includes(run.status));
  const createMissingFields = [
    ["name", "name"],
    ["objective", "objective"],
    ["hypothesis", "hypothesis"],
  ]
    .filter(([key]) => !String(newExp[key] ?? "").trim())
    .map(([, label]) => label);
  const hasStartedCreate = [
    newExp.name,
    newExp.objective,
    newExp.hypothesis,
  ].some((value) => String(value ?? "").trim());
  const openInvestigation = (item) => {
    if (item.id !== expId) switchExperiment(item.id);
    setNotice(`Opened investigation: ${item.name}.`);
    requestAnimationFrame(() => {
      document.getElementById("active-investigation-title")?.scrollIntoView({
        behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
          .matches
          ? "auto"
          : "smooth",
        block: "start",
      });
    });
  };
  const editMissingFields = editExp
    ? ["name", "objective", "hypothesis"].filter(
        (key) => !String(editExp[key] ?? "").trim(),
      )
    : [];

  return (
    <div className="investigations-page">
      <div className="investigation-columns">
        <details className="investigation-create-disclosure">
          <summary>＋ New investigation</summary>
          <Panel title="Define an investigation">
            <p className="panel-intro">
              Write down what you want to learn before you compare approaches.
              You can add a conclusion after reviewing the evidence.
            </p>
            <form
              className="investigation-form"
              onSubmit={(e) => {
                e.preventDefault();
                act(async () => {
                  const id = "exp_" + crypto.randomUUID().replaceAll("-", "");
                  await request("/experiments/", "POST", {
                    id,
                    ...newExp,
                    target_accuracy: null,
                    target_latency_ms: null,
                    conclusion: undefined,
                    archived: undefined,
                  });
                  switchExperiment(id);
                  setNewExp(emptyExperiment);
                  setTab("Training");
                  setNotice(
                    "Investigation created. Configure your first approach.",
                  );
                });
              }}
            >
              <RequiredFieldLegend />
              <Field
                label="Investigation name"
                value={newExp.name}
                onChange={(v) => setNewExp({ ...newExp, name: v })}
                placeholder="e.g. Improve CIFAR-100 validation accuracy"
                required
              />
              <Field
                label="Objective"
                type="textarea"
                value={newExp.objective}
                onChange={(v) => setNewExp({ ...newExp, objective: v })}
                placeholder="What problem are you trying to solve?"
                required
              />
              <Field
                label="Hypothesis"
                type="textarea"
                value={newExp.hypothesis}
                onChange={(v) => setNewExp({ ...newExp, hypothesis: v })}
                placeholder="What do you expect to happen, and why?"
                required
              />
              <TagsField
                value={newExp.tags}
                onChange={(tags) => setNewExp({ ...newExp, tags })}
              />
              <div className="form-footer">
                {hasStartedCreate && createMissingFields.length > 0 && (
                  <span role="status" aria-live="polite">
                    Still required: {createMissingFields.join(", ")}.
                  </span>
                )}
                <button
                  className="primary create-investigation"
                  disabled={busy || !online || createMissingFields.length > 0}
                >
                  <span aria-hidden="true">＋</span> Create investigation
                </button>
              </div>
            </form>
          </Panel>
        </details>

        <Panel title="Saved investigations">
          <p className="panel-intro">
            Search by name or ID, then open a record to continue its work.
          </p>
          <div className="investigation-search-row">
            <Field
              label="Search investigations"
              value={query}
              onChange={setQuery}
              type="search"
              placeholder="Search name or ID"
            />
            <span className="result-count" aria-live="polite">
              {filteredExperiments.length} shown
            </span>
          </div>
          {filteredExperiments.length ? (
            <>
              <div
                className="table-wrap"
                role="region"
                aria-label="Saved investigations"
              >
                <table className="investigation-records-table">
                  <caption>Saved investigation records</caption>
                  <thead>
                    <tr>
                      <th scope="col">Investigation</th>
                      <th scope="col">Objective</th>
                      <th scope="col">Status</th>
                      <th scope="col">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredExperiments.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <strong>{item.name}</strong>
                          {item.id === expId && <small>Currently open</small>}
                        </td>
                        <td className="investigation-objective-cell">
                          {evidenceText(item.objective)}
                        </td>
                        <td>
                          <span
                            className={`record-state ${item.archived ? "is-archived" : "is-active"}`}
                          >
                            {item.archived ? "Archived" : "Active"}
                          </span>
                        </td>
                        <td>
                          <button
                            className="link"
                            type="button"
                            aria-current={
                              item.id === expId ? "page" : undefined
                            }
                            onClick={() => openInvestigation(item)}
                          >
                            {item.id === expId ? "Open" : "Resume"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="investigation-empty">
              <span aria-hidden="true">✳</span>
              <strong>
                {experiments.length
                  ? "No matching investigations"
                  : "No investigations yet"}
              </strong>
              <p>
                {experiments.length
                  ? "Try another name or ID."
                  : "Create your first investigation to begin tracking the work."}
              </p>
            </div>
          )}
        </Panel>
      </div>

      {experiment && (
        <section
          className="active-investigation"
          aria-labelledby="active-investigation-title"
        >
          <div className="active-record-heading">
            <div>
              <span className="section-kicker">CURRENT INVESTIGATION</span>
              <h2 id="active-investigation-title">{experiment.name}</h2>
              <code>{experiment.id}</code>
            </div>
            <button
              className="edit-record-button"
              type="button"
              onClick={() => setEditExp({ ...emptyExperiment, ...experiment })}
            >
              Edit record
            </button>
          </div>
          {editExp ? (
            <form
              className="edit-investigation-form"
              onSubmit={(e) => {
                e.preventDefault();
                act(async () => {
                  const payload = Object.fromEntries(
                    Object.keys(emptyExperiment).map((k) => [k, editExp[k]]),
                  );
                  await request(`/experiments/${expId}`, "PATCH", payload);
                  setEditExp(null);
                  setNotice("Investigation updated.");
                });
              }}
            >
              <RequiredFieldLegend />
              {Object.keys(editLabels).map((key) => (
                <Field
                  key={key}
                  label={editLabels[key]}
                  value={editExp[key]}
                  type={key === "name" ? "text" : "textarea"}
                  required={key !== "conclusion"}
                  onChange={(v) => setEditExp({ ...editExp, [key]: v })}
                />
              ))}
              <TagsField
                value={editExp.tags || {}}
                onChange={(tags) => setEditExp({ ...editExp, tags })}
              />
              <label className="check archive-check">
                <input
                  type="checkbox"
                  checked={!!editExp.archived}
                  onChange={(e) =>
                    setEditExp({ ...editExp, archived: e.target.checked })
                  }
                />
                Archive investigation
              </label>
              <div className="form-footer">
                <span>
                  {editMissingFields.length
                    ? `Required before saving: ${editMissingFields.join(", ")}.`
                    : "Archiving prevents new runs but keeps existing records."}
                </span>
                <div className="edit-actions">
                  <button
                    className="primary"
                    disabled={busy || editMissingFields.length > 0}
                  >
                    Save changes
                  </button>
                  <button type="button" onClick={() => setEditExp(null)}>
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <>
              <div className="active-record-content">
                <div className="investigation-notes">
                  <div className="note-block">
                    <span>OBJECTIVE</span>
                    <p>{evidenceText(experiment.objective)}</p>
                  </div>
                  <div className="note-block">
                    <span>HYPOTHESIS</span>
                    <p>{evidenceText(experiment.hypothesis)}</p>
                  </div>
                  <div className="note-block conclusion-note">
                    <span>CONCLUSION</span>
                    <p>
                      {experiment.conclusion ||
                        "Not recorded yet. Add a conclusion after reviewing the results."}
                    </p>
                  </div>
                </div>
                <div className="investigation-progress-card">
                  <span className="section-kicker">EVIDENCE SO FAR</span>
                  <div className="progress-numbers">
                    <div>
                      <strong>{runs.length}</strong>
                      <span>runs</span>
                    </div>
                    <div>
                      <strong>{completedRuns}</strong>
                      <span>completed</span>
                    </div>
                  </div>
                  <button
                    className="primary configure-approach"
                    disabled={!!experiment.archived}
                    onClick={() => setTab("Training")}
                  >
                    {experiment.archived
                      ? "Investigation archived"
                      : activeRun
                        ? "View locked configuration →"
                        : "Configure an approach →"}
                  </button>
                  {Boolean(experiment.archived) && (
                    <small>Unarchive this record to add new runs.</small>
                  )}
                  {!experiment.archived && activeRun && (
                    <small>
                      Run {activeRun.approach_name} is{" "}
                      {activeRun.status.toLowerCase()}. Its settings are
                      read-only until it finishes.
                    </small>
                  )}
                </div>
              </div>
              <InvestigationTimeline
                runs={runs}
                onOpenRun={(selectedRun) => {
                  setRunId(selectedRun.id);
                  setTab("Training");
                }}
                onBranch={branch}
              />
              <div className="report-links">
                <span>EXPORT EVIDENCE</span>
                <a href={`/api/v1/experiments/${expId}/report`}>
                  Full decision report <span aria-hidden="true">↗</span>
                </a>
                <a href={`/api/v1/experiments/${expId}/report.csv`}>
                  Comparison &amp; epoch metrics CSV{" "}
                  <span aria-hidden="true">↗</span>
                </a>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
