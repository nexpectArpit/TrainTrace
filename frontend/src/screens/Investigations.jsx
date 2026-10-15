import React from "react";
import { request } from "../services/api";
import { emptyExperiment, Field, Panel } from "../components/Common";
export default function Investigations({ workspace }) {
  const {
    setTab,
    expId,
    experiments,
    runs,
    online,
    setNotice,
    busy,
    newExp,
    setNewExp,
    editExp,
    setEditExp,
    decision,
    experiment,
    act,
    switchExperiment,
  } = workspace;
  return (
    <>
      <Panel title="Define an investigation">
        <p>
          Record the problem and hypothesis before testing an approach. Accuracy
          targets use 0–100%.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              const id = "exp_" + crypto.randomUUID().replaceAll("-", "");
              await request("/experiments/", "POST", {
                id,
                ...newExp,
                conclusion: undefined,
                archived: undefined,
              });
              switchExperiment(id);
              setNewExp(emptyExperiment);
              setNotice("Investigation created.");
            });
          }}
        >
          <div className="grid two">
            <Field
              label="Investigation name"
              value={newExp.name}
              onChange={(v) => setNewExp({ ...newExp, name: v })}
              required
            />
            <Field
              label="Target test accuracy (%)"
              type="number"
              min="0"
              max="100"
              step="any"
              value={newExp.target_accuracy}
              onChange={(v) => setNewExp({ ...newExp, target_accuracy: v })}
            />
          </div>
          <Field
            label="Objective"
            type="textarea"
            value={newExp.objective}
            onChange={(v) => setNewExp({ ...newExp, objective: v })}
            required
          />
          <Field
            label="Hypothesis"
            type="textarea"
            value={newExp.hypothesis}
            onChange={(v) => setNewExp({ ...newExp, hypothesis: v })}
            required
          />
          <Field
            label="Target latency per sample (ms, optional)"
            type="number"
            step="any"
            min="0.000001"
            value={newExp.target_latency_ms}
            onChange={(v) => setNewExp({ ...newExp, target_latency_ms: v })}
          />
          <button className="primary" disabled={busy || !online}>
            Create investigation
          </button>
        </form>
      </Panel>
      {experiment && (
        <Panel
          title="Investigation record"
          action={
            <button
              onClick={() => setEditExp({ ...emptyExperiment, ...experiment })}
            >
              Edit record
            </button>
          }
        >
          {editExp ? (
            <form
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
              {["name", "objective", "hypothesis", "conclusion"].map((k) => (
                <Field
                  key={k}
                  label={k}
                  value={editExp[k]}
                  type={k === "name" ? "text" : "textarea"}
                  required={k !== "conclusion"}
                  onChange={(v) => setEditExp({ ...editExp, [k]: v })}
                />
              ))}
              <div className="grid two">
                {["target_accuracy", "target_latency_ms"].map((k) => (
                  <Field
                    key={k}
                    label={k}
                    type="number"
                    min="0"
                    step="any"
                    value={editExp[k]}
                    onChange={(v) => setEditExp({ ...editExp, [k]: v })}
                  />
                ))}
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  checked={!!editExp.archived}
                  onChange={(e) =>
                    setEditExp({ ...editExp, archived: e.target.checked })
                  }
                />
                Archive investigation
              </label>
              <button className="primary" disabled={busy}>
                Save
              </button>
              <button type="button" onClick={() => setEditExp(null)}>
                Cancel
              </button>
            </form>
          ) : (
            <>
              <p>Conclusion: {experiment.conclusion || "Not recorded"}</p>
              <a href={`/api/v1/experiments/${expId}/report`}>
                Download decision report
              </a>
              <p>
                {runs.length} candidate runs ·{" "}
                {runs.filter((r) => r.status === "COMPLETED").length} completed
              </p>
              <button onClick={() => setTab("Training")}>
                Configure an approach →
              </button>
            </>
          )}
        </Panel>
      )}
    </>
  );
}
