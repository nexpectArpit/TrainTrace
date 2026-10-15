"""SQLite schema migrations. Legacy records are preserved with unknown provenance."""

import sqlite3
from contextlib import contextmanager, closing
from config import DB_PATH


def get_db_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def database():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with database() as c:
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version == 0 and c.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone():
            backup = DB_PATH.with_suffix(".pre-v1.db")
            if not backup.exists():
                with closing(sqlite3.connect(backup)) as target:
                    c.backup(target)
        c.executescript("""
        CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, name TEXT NOT NULL, objective TEXT NOT NULL,
          target_accuracy REAL, target_latency_ms REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiments(id),
          approach_name TEXT NOT NULL, model_architecture TEXT NOT NULL, batch_size INTEGER NOT NULL,
          epochs INTEGER NOT NULL, learning_rate REAL NOT NULL, seed INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'QUEUED', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS epoch_metrics(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
          epoch INTEGER NOT NULL, train_loss REAL NOT NULL, train_acc REAL NOT NULL, val_loss REAL NOT NULL,
          val_acc REAL NOT NULL, epoch_time_sec REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
          status TEXT NOT NULL, rationale TEXT NOT NULL, timestamp TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
          run_id TEXT NOT NULL REFERENCES runs(id), checkpoint_path TEXT NOT NULL, test_accuracy REAL,
          latency_ms REAL, status TEXT NOT NULL DEFAULT 'REGISTERED', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'QUEUED', cancel_requested INTEGER NOT NULL DEFAULT 0,
          error TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
          message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
          kind TEXT NOT NULL, path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS audits(id TEXT PRIMARY KEY REFERENCES jobs(id), run_id TEXT NOT NULL REFERENCES runs(id),
          protocol TEXT NOT NULL, report TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS serving(id INTEGER PRIMARY KEY CHECK(id=1), model_id TEXT NOT NULL REFERENCES models(id));
        CREATE INDEX IF NOT EXISTS run_experiment ON runs(experiment_id);
        CREATE INDEX IF NOT EXISTS metric_run ON epoch_metrics(run_id,epoch);
        CREATE INDEX IF NOT EXISTS event_run ON events(run_id,id);
        """)
        additions = {
            "experiments": {
                "hypothesis": "TEXT NOT NULL DEFAULT ''",
                "conclusion": "TEXT NOT NULL DEFAULT ''",
                "archived": "INTEGER NOT NULL DEFAULT 0",
                "parent_run_id": "TEXT REFERENCES runs(id)",
            },
            "runs": {
                "config_json": "TEXT",
                "environment_json": "TEXT",
                "dataset_json": "TEXT",
                "predecessor_run_id": "TEXT REFERENCES runs(id)",
                "motivating_reason": "TEXT NOT NULL DEFAULT ''",
                "evaluation_json": "TEXT",
                "error": "TEXT",
                "progress_json": "TEXT",
                "audit_id": "TEXT REFERENCES audits(id)",
            },
            "decisions": {"details_json": "TEXT", "evidence_json": "TEXT"},
            "models": {"manifest_json": "TEXT", "sha256": "TEXT"},
            "epoch_metrics": {"learning_rate": "REAL"},
        }
        for table, fields in additions.items():
            existing = {row["name"] for row in c.execute(f"PRAGMA table_info({table})")}
            for name, definition in fields.items():
                if name not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        c.executescript("""
        CREATE TRIGGER IF NOT EXISTS unique_new_epoch BEFORE INSERT ON epoch_metrics
        WHEN EXISTS(SELECT 1 FROM epoch_metrics WHERE run_id=NEW.run_id AND epoch=NEW.epoch)
        BEGIN SELECT RAISE(ABORT, 'Epoch already recorded'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_model_version BEFORE INSERT ON models
        WHEN EXISTS(SELECT 1 FROM models WHERE name=NEW.name AND ltrim(version,'v')=ltrim(NEW.version,'v'))
        BEGIN SELECT RAISE(ABORT, 'Model name/version already registered'); END;
        """)
        c.execute("PRAGMA user_version=1")
