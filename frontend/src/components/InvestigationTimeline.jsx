import React from "react";
import { Badge, fmt } from "./Common";
import styles from "./InvestigationTimeline.module.css";

export default function InvestigationTimeline({ runs, onOpenRun, onBranch }) {
  const byId = new Map(runs.map((run) => [run.id, run]));
  const ordered = [...runs].sort((a, b) => {
    const left = Date.parse(a.created_at || a.queued_at || "") || 0;
    const right = Date.parse(b.created_at || b.queued_at || "") || 0;
    return left - right;
  });

  return (
    <section
      className={styles.timeline}
      aria-labelledby="investigation-timeline-title"
    >
      <div className={styles.heading}>
        <div>
          <h3 id="investigation-timeline-title">Approach timeline</h3>
          <p>
            Recorded runs and their decisions, in creation order. A predecessor
            link describes an iteration; it does not imply inherited weights.
          </p>
        </div>
        <span>
          {ordered.length} {ordered.length === 1 ? "approach" : "approaches"}
        </span>
      </div>
      {ordered.length ? (
        <ol className={styles.list}>
          {ordered.map((run) => {
            const predecessor = byId.get(run.predecessor_run_id);
            return (
              <li key={run.id} className={styles.item}>
                <div className={styles.itemMain}>
                  <strong>{run.approach_name || "Unnamed approach"}</strong>
                  <span className={styles.meta}>
                    {predecessor
                      ? `Follows ${predecessor.approach_name}`
                      : run.predecessor_run_id
                        ? "Predecessor outside this investigation"
                        : "Initial approach"}
                    {" · "}
                    {run.model_architecture || "Architecture unknown"}
                  </span>
                  {run.motivating_reason && <p>{run.motivating_reason}</p>}
                  {run.latest_decision?.rationale && (
                    <p className={styles.rationale}>
                      {run.latest_decision.rationale}
                    </p>
                  )}
                </div>
                <div className={styles.evidence}>
                  <Badge value={run.status} />
                  <Badge value={run.latest_decision?.status || "CANDIDATE"} />
                  <span>
                    {run.best_val_accuracy == null
                      ? "Validation unmeasured"
                      : `Best validation ${fmt(run.best_val_accuracy)}%`}
                  </span>
                </div>
                <div className={styles.actions}>
                  <button type="button" onClick={() => onOpenRun(run)}>
                    Open run
                  </button>
                  {run.latest_decision && (
                    <button type="button" onClick={() => onBranch(run)}>
                      Iterate from this
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className={styles.empty}>
          No runs yet. Configure the first approach to begin the evidence chain.
        </p>
      )}
    </section>
  );
}
