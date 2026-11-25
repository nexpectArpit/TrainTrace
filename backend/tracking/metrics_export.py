"""Produce readable CSV artifacts from durable SQLite epoch metrics."""

import csv

from db.database import database
from storage import record_artifact, run_artifact_path

def initialize_metrics_csv(run_id):
    """Create the notebook-friendly metrics stream once before the first epoch."""
    columns = [row["name"] for row in database_connection_columns()]
    path = run_artifact_path(run_id, f"{run_id}_metrics.csv", "metrics")
    with path.open("w", newline="") as stream:
        csv.DictWriter(stream, fieldnames=columns).writeheader()
        # No fsync here: the CSV is a convenience export artifact.
        # Epoch metrics are durably stored in SQLite (WAL mode); the CSV
        # is rebuilt from the database if needed.
    return path


def database_connection_columns():
    with database() as c:
        return [dict(r) for r in c.execute("PRAGMA table_info(epoch_metrics)")]


def append_metrics_csv(run_id, epoch):
    with database() as c:
        row = c.execute(
            "SELECT * FROM epoch_metrics WHERE run_id=? AND epoch=? ORDER BY id DESC LIMIT 1",
            (run_id, epoch),
        ).fetchone()
    if not row:
        return None
    path = run_artifact_path(run_id, f"{run_id}_metrics.csv", "metrics")
    with path.open("a", newline="") as stream:
        csv.DictWriter(stream, fieldnames=list(dict(row))).writerow(dict(row))
        # No fsync: epoch metrics are already committed to SQLite WAL.
        # The OS page cache will flush the CSV to disk on its own schedule.
    return path


def publish_metrics_csv(run_id):
    path = run_artifact_path(run_id, f"{run_id}_metrics.csv", "metrics")
    if path.is_file() and path.stat().st_size:
        record_artifact(run_id, "metrics_csv", path)

