"""Ordered SQLite schema upgrades. Each migration is safe to re-enter."""

from collections.abc import Callable
import json
import sqlite3
from pathlib import Path


def _add_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _migration_2(conn: sqlite3.Connection) -> None:
    """Separate selection-time validation from one-time final test evaluation."""
    _add_column(conn, "runs", "validation_json", "TEXT")
    _add_column(conn, "runs", "final_evaluation_json", "TEXT")
    _add_column(conn, "runs", "final_evaluation_status", "TEXT NOT NULL DEFAULT 'NOT_STARTED'")
    _add_column(conn, "runs", "final_evaluation_job_id", "TEXT")
    _add_column(conn, "runs", "final_evaluation_error", "TEXT")
    _add_column(conn, "runs", "config_schema_version", "INTEGER NOT NULL DEFAULT 1")
    _add_column(conn, "experiments", "tags_json", "TEXT NOT NULL DEFAULT '{}' ")
    _add_column(conn, "runs", "tags_json", "TEXT NOT NULL DEFAULT '{}' ")
    _add_column(conn, "models", "tags_json", "TEXT NOT NULL DEFAULT '{}' ")
    # Existing evaluation_json values came from the old pipeline's test-set pass.
    # Preserve them as historical final evaluations; never reinterpret them as validation.
    historical = conn.execute(
        "SELECT id,evaluation_json FROM runs WHERE evaluation_json IS NOT NULL "
        "AND final_evaluation_json IS NULL"
    ).fetchall()
    for row in historical:
        try:
            evaluation = json.loads(row["evaluation_json"])
            if isinstance(evaluation, dict):
                evaluation["legacy_preselection_test_exposure"] = True
                evaluation["metric_set"] = "historical_test"
                value = json.dumps(evaluation)
            else:
                value = row["evaluation_json"]
        except (TypeError, json.JSONDecodeError):
            value = row["evaluation_json"]
        conn.execute(
            "UPDATE runs SET final_evaluation_json=?,final_evaluation_status='HISTORICAL' WHERE id=?",
            (value, row["id"]),
        )
    legacy_runs = conn.execute(
        "SELECT id FROM runs WHERE validation_json IS NULL AND status='COMPLETED'"
    ).fetchall()
    for row in legacy_runs:
        metric = conn.execute(
            "SELECT val_loss,val_acc,epoch FROM epoch_metrics WHERE run_id=? "
            "ORDER BY val_acc DESC,epoch DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
        if metric:
            conn.execute(
                "UPDATE runs SET validation_json=? WHERE id=?",
                (
                    json.dumps(
                        {
                            "metric_set": "validation",
                            "validation_loss": metric["val_loss"],
                            "validation_accuracy": metric["val_acc"],
                            "checkpoint_epoch": metric["epoch"],
                            "legacy_snapshot": True,
                        }
                    ),
                    row["id"],
                ),
            )
    conn.execute("CREATE INDEX IF NOT EXISTS decision_run_id ON decisions(run_id,id)")
    conn.execute("CREATE INDEX IF NOT EXISTS artifact_run_id ON artifacts(run_id,created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS job_status_created ON jobs(status,created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS audit_run_id ON audits(run_id,created_at)")


def _migration_3(conn: sqlite3.Connection) -> None:
    """Permit at most one final-test candidate per investigation."""
    _add_column(conn, "experiments", "final_evaluation_run_id", "TEXT")
    conn.execute(
        "UPDATE experiments SET final_evaluation_run_id=("
        "SELECT id FROM runs WHERE runs.experiment_id=experiments.id "
        "AND final_evaluation_json IS NOT NULL ORDER BY created_at,id LIMIT 1) "
        "WHERE final_evaluation_run_id IS NULL"
    )


def _migration_4(conn: sqlite3.Connection) -> None:
    """Replace managed absolute paths with keys relative to the storage adapter root."""
    from config import ARTIFACTS_DIR, REGISTRY_DIR

    for row in conn.execute("SELECT id,path FROM artifacts").fetchall():
        path = Path(row["path"])
        if path.is_absolute():
            resolved = path.resolve()
            if resolved.is_relative_to(ARTIFACTS_DIR.resolve()):
                conn.execute(
                    "UPDATE artifacts SET path=? WHERE id=?",
                    (resolved.relative_to(ARTIFACTS_DIR.resolve()).as_posix(), row["id"]),
                )
    for row in conn.execute("SELECT id,checkpoint_path FROM models").fetchall():
        path = Path(row["checkpoint_path"])
        if path.is_absolute():
            resolved = path.resolve()
            if resolved.is_relative_to(REGISTRY_DIR.resolve()):
                conn.execute(
                    "UPDATE models SET checkpoint_path=? WHERE id=?",
                    (resolved.relative_to(REGISTRY_DIR.resolve()).as_posix(), row["id"]),
                )


def _migration_5(conn: sqlite3.Connection) -> None:
    """Track optional external synchronization separately from run config."""
    _add_column(conn, "runs", "tracking_json", "TEXT")


def _migration_6(conn: sqlite3.Connection) -> None:
    """Retain sampled batch signals for charts after reload and completion."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS run_progress_samples("
        "id INTEGER PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),"
        "epoch INTEGER NOT NULL,batch_idx INTEGER NOT NULL,total_batches INTEGER NOT NULL,"
        "batch_loss REAL NOT NULL,running_acc REAL NOT NULL,samples_per_sec REAL,device_memory_mb REAL,"
        "observed_at INTEGER NOT NULL,UNIQUE(run_id,epoch,batch_idx))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS progress_sample_run ON run_progress_samples(run_id,id)"
    )


def _migration_7(conn: sqlite3.Connection) -> None:
    """Add accelerator memory samples to existing progress histories."""
    _add_column(conn, "run_progress_samples", "device_memory_mb", "REAL")


def _migration_8(conn: sqlite3.Connection) -> None:
    """Persist worker CPU and peak memory measurements."""
    _add_column(conn, "run_progress_samples", "worker_cpu_percent", "REAL")
    _add_column(conn, "run_progress_samples", "peak_rss_mb", "REAL")


def _migration_9(conn: sqlite3.Connection) -> None:
    """Add compound (run_id, epoch, batch_idx) index on progress samples for faster chart reads."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS progress_sample_run_epoch "
        "ON run_progress_samples(run_id, epoch, batch_idx)"
    )


def _migration_10(conn: sqlite3.Connection) -> None:
    """Persist accelerator telemetry emitted by remote workers."""
    for name in (
        "gpu_utilization_pct",
        "gpu_memory_used_mb",
        "gpu_memory_total_mb",
        "gpu_temperature_c",
        "gpu_power_watts",
    ):
        _add_column(conn, "run_progress_samples", name, "REAL")


def _migration_11(conn: sqlite3.Connection) -> None:
    """Add derived GPU memory utilization without rewriting migration 10."""
    _add_column(conn, "run_progress_samples", "gpu_memory_utilization_pct", "REAL")


MIGRATIONS: tuple[tuple[int, Callable[[sqlite3.Connection], None]], ...] = (
    (2, _migration_2),
    (3, _migration_3),
    (4, _migration_4),
    (5, _migration_5),
    (6, _migration_6),
    (7, _migration_7),
    (8, _migration_8),
    (9, _migration_9),
    (10, _migration_10),
    (11, _migration_11),
)
