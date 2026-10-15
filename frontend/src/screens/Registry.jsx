import React from "react";
import { formatTime } from "../components/Common";
import { request } from "../services/api";
import { fmt, Badge, Field, Panel, Json } from "../components/Common";
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
    act,
    loadLineage,
  } = workspace;
  return (
    <>
      <Panel title="Register selected evidence">
        <p>
          Registration freezes the evaluated weights, decision and investigation
          history. Names and semantic versions are immutable. Activation for
          inference is a separate step.
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
              setLineage(await request(`/registry/${result.model.id}/lineage`));
            });
          }}
        >
          <div className="grid two">
            <Field
              label="Release name"
              pattern="[A-Za-z0-9][A-Za-z0-9_-]{0,79}"
              value={release.name}
              onChange={(v) => setRelease({ ...release, name: v })}
              required
            />
            <Field
              label="Semantic version"
              value={release.version}
              onChange={(v) => setRelease({ ...release, version: v })}
              placeholder="v1.0.0"
              required
            />
          </div>
          <button
            className="primary"
            disabled={
              busy ||
              !online ||
              run?.latest_decision?.status !== "SELECTED" ||
              !run?.config
            }
          >
            Register selected candidate
          </button>
        </form>
      </Panel>
      <Panel title="Registered versions">
        {models
          .filter(
            (m) =>
              !query ||
              (m.name + " " + m.run_id)
                .toLowerCase()
                .includes(query.toLowerCase()),
          )
          .map((m) => (
            <article className="record" key={m.id}>
              <h3>
                {m.name}:{m.version}{" "}
                <Badge
                  value={
                    activeModel === m.id
                      ? "ACTIVE"
                      : m.sha256
                        ? "REGISTERED"
                        : "LEGACY UNVERIFIED"
                  }
                />
              </h3>
              <p>
                Run {m.run_id} · test {fmt(m.test_accuracy)}% ·{" "}
                {formatTime(m.created_at)}
              </p>
              <div className="actions">
                <button disabled={busy} onClick={() => loadLineage(m.id)}>
                  View frozen lineage
                </button>
                <button
                  disabled={busy || !m.sha256 || !online}
                  onClick={() =>
                    act(async () => {
                      await request(`/registry/${m.id}/activate`, "POST");
                      setPrediction(null);
                      setNotice("Registered version activated for inference.");
                    })
                  }
                >
                  Activate for inference
                </button>
              </div>
            </article>
          ))}
        {!models.length && <div className="empty">No registered versions.</div>}
      </Panel>
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
              {lineage.investigation_history.map((r) => (
                <article className="record" key={r.id}>
                  <h3>{r.approach_name}</h3>
                  <p>
                    Predecessor: {r.predecessor_run_id || "None recorded"} ·{" "}
                    {r.motivating_reason || "No motivation recorded"}
                  </p>
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
    </>
  );
}
