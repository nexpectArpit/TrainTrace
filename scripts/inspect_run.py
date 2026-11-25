"""Read-only, dependency-free view of a TrainTrace run and its evidence."""

import argparse
import json
import os
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = Path(os.environ.get("TRAINTRACE_STORAGE_DIR", ROOT / "backend/storage")).resolve()
DB = STORAGE / "db/traintrace.db"
ARTIFACTS = STORAGE / "artifacts"


def rows(conn, sql, parameters=()):
    return [dict(row) for row in conn.execute(sql, parameters)]


def has_table(conn, name):
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )


def read_json(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"unreadable_json": value}


def inspect(conn, run_id, include_replays, all_epochs):
    if run_id:
        run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    else:
        where = "" if include_replays else "WHERE audit_id IS NULL"
        run = conn.execute(
            f"SELECT * FROM runs {where} ORDER BY created_at DESC,rowid DESC LIMIT 1"
        ).fetchone()
    if run is None:
        raise ValueError(f"Run {run_id!r} was not found" if run_id else "No runs found")

    run = dict(run)
    decision = conn.execute(
        "SELECT status FROM decisions WHERE run_id=? ORDER BY id DESC LIMIT 1",
        (run["id"],),
    ).fetchone() if has_table(conn, "decisions") else None
    final_record = read_json(run.get("final_evaluation_json"))
    final_visible = (
        run.get("final_evaluation_status") == "COMPLETED"
        and decision is not None
        and decision["status"] == "SELECTED"
        and isinstance(final_record, dict)
        and not final_record.get("legacy_preselection_test_exposure")
    )
    metrics = rows(
        conn,
        "SELECT epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate "
        "FROM epoch_metrics WHERE run_id=? ORDER BY epoch,id",
        (run["id"],),
    )
    samples = (
        rows(
            conn,
            "SELECT * FROM run_progress_samples WHERE run_id=? ORDER BY id DESC LIMIT 1",
            (run["id"],),
        )
        if has_table(conn, "run_progress_samples")
        else []
    )
    artifacts = rows(
        conn,
        "SELECT kind,path,size_bytes,created_at FROM artifacts WHERE run_id=? "
        "ORDER BY created_at,id",
        (run["id"],),
    )
    for artifact in artifacts:
        # Never follow a legacy or corrupt path outside the managed artifact directory.
        path = (ARTIFACTS / artifact["path"]).resolve()
        artifact["file"] = str(path) if path.is_relative_to(ARTIFACTS) else "INVALID PATH"
        artifact["exists"] = path.is_file() if path.is_relative_to(ARTIFACTS) else False

    return {
        "run_id": run["id"],
        "status": run["status"],
        "created_at": run["created_at"],
        "experiment_id": run["experiment_id"],
        "approach_name": run["approach_name"],
        "epochs_requested": run["epochs"],
        "epochs_saved": len(metrics),
        "latest_epoch": metrics[-1] if metrics else None,
        "epoch_metrics": metrics if all_epochs else None,
        "current_progress": read_json(run.get("progress_json")),
        "latest_batch_sample": samples[0] if samples else None,
        "error": run.get("error"),
        "final_evaluation_status": run.get("final_evaluation_status"),
        "final_evaluation": final_record if final_visible else None,
        "final_evaluation_visibility": "available" if final_visible else "sealed or not eligible",
        "final_evaluation_error": run.get("final_evaluation_error"),
        "artifacts": artifacts,
        "database": str(DB),
    }


def print_report(report):
    print(f"Run: {report['run_id']}  [{report['status']}]")
    print(f"Created: {report['created_at']}  Investigation: {report['experiment_id']}")
    print(f"Approach: {report['approach_name']}")
    print(f"Epochs saved: {report['epochs_saved']}/{report['epochs_requested']}")
    if report["latest_epoch"]:
        epoch = report["latest_epoch"]
        print(
            f"Latest epoch {epoch['epoch']}: train acc {epoch['train_acc']:.2f}%, "
            f"val acc {epoch['val_acc']:.2f}%, train loss {epoch['train_loss']:.4f}, "
            f"val loss {epoch['val_loss']:.4f}"
        )
    if report["latest_batch_sample"]:
        sample = report["latest_batch_sample"]
        print(
            f"Latest batch: epoch {sample['epoch']}, "
            f"batch {sample['batch_idx']}/{sample['total_batches']}"
        )
    if report["current_progress"] and report["status"] not in {"COMPLETED", "FAILED", "STOPPED"}:
        print("Progress:", json.dumps(report["current_progress"], sort_keys=True))
    if report["error"]:
        print("Run error:", report["error"])
    if report["final_evaluation_status"]:
        print("Final evaluation:", report["final_evaluation_status"])
    if report["final_evaluation_visibility"] != "available":
        print("Final evidence:", report["final_evaluation_visibility"])
    if report["final_evaluation_error"]:
        print("Evaluation error:", report["final_evaluation_error"])
    if report["final_evaluation"]:
        evaluation = report["final_evaluation"]
        summary = {
            key: evaluation[key]
            for key in ("test_accuracy", "test_loss", "samples", "checkpoint_epoch")
            if key in evaluation
        }
        if summary:
            print("Evaluation:", json.dumps(summary, sort_keys=True))
    print("Database:", report["database"])
    print("Artifacts:")
    if not report["artifacts"]:
        print("  (none yet)")
    for artifact in report["artifacts"]:
        state = "" if artifact["exists"] else " [MISSING]"
        print(f"  {artifact['kind']}: {artifact['file']}{state}")
    if report["epoch_metrics"] is not None:
        print("All epochs:")
        for epoch in report["epoch_metrics"]:
            print(" ", json.dumps(epoch, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Inspect this run instead of the latest main run")
    parser.add_argument(
        "--include-replays",
        action="store_true",
        help="Include audit replay runs in latest selection",
    )
    parser.add_argument("--all-epochs", action="store_true", help="Print every saved epoch")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    if not DB.is_file():
        parser.exit(
            1, f"Database not found: {DB}\nStart the API once or set TRAINTRACE_STORAGE_DIR.\n"
        )
    try:
        with sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            report = inspect(conn, args.run_id, args.include_replays, args.all_epochs)
    except (sqlite3.Error, ValueError) as exc:
        parser.exit(1, f"Cannot inspect run: {exc}\n")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
