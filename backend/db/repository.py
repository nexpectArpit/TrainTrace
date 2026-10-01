"""
traintrace/backend/db/repository.py
===================================
Database CRUD Repository Helper Functions for Experiments, Runs, Metrics, and Decisions.
"""

import sqlite3
from typing import Dict, Any, List, Optional


# =============================================================================
# EXPERIMENT CRUD
# =============================================================================
def create_experiment(
    conn: sqlite3.Connection,
    exp_id: str,
    name: str,
    objective: str,
    target_accuracy: Optional[float] = None,
    target_latency_ms: Optional[float] = None
) -> None:
    """Inserts a new experiment parent record."""
    conn.execute(
        """
        INSERT INTO experiments (id, name, objective, target_accuracy, target_latency_ms)
        VALUES (?, ?, ?, ?, ?);
        """,
        (exp_id, name, objective, target_accuracy, target_latency_ms)
    )
    conn.commit()


def get_experiment(conn: sqlite3.Connection, exp_id: str) -> Optional[Dict[str, Any]]:
    """Fetches single experiment record by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments WHERE id = ?;", (exp_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# =============================================================================
# RUN CRUD
# =============================================================================
def create_run(
    conn: sqlite3.Connection,
    run_id: str,
    experiment_id: str,
    approach_name: str,
    model_architecture: str,
    batch_size: int,
    epochs: int,
    learning_rate: float,
    seed: int,
    status: str = "QUEUED"
) -> None:
    """Inserts a new run record."""
    conn.execute(
        """
        INSERT INTO runs (id, experiment_id, approach_name, model_architecture, batch_size, epochs, learning_rate, seed, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (run_id, experiment_id, approach_name, model_architecture, batch_size, epochs, learning_rate, seed, status)
    )
    conn.commit()


def update_run_status(conn: sqlite3.Connection, run_id: str, status: str) -> None:
    """Updates status of a run (e.g., RUNNING, COMPLETED, FAILED)."""
    conn.execute("UPDATE runs SET status = ? WHERE id = ?;", (status, run_id))
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> Optional[Dict[str, Any]]:
    """Fetches run record by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?;", (run_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# =============================================================================
# METRIC & DECISION CRUD
# =============================================================================
def save_epoch_metric(
    conn: sqlite3.Connection,
    run_id: str,
    epoch: int,
    train_loss: float,
    train_acc: float,
    val_loss: float,
    val_acc: float,
    epoch_time_sec: float
) -> None:
    """Saves per-epoch scalar metrics."""
    conn.execute(
        """
        INSERT INTO epoch_metrics (run_id, epoch, train_loss, train_acc, val_loss, val_acc, epoch_time_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (run_id, epoch, train_loss, train_acc, val_loss, val_acc, epoch_time_sec)
    )
    conn.commit()


def get_run_metrics(conn: sqlite3.Connection, run_id: str) -> List[Dict[str, Any]]:
    """Fetches all epoch metrics recorded for a run."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM epoch_metrics WHERE run_id = ? ORDER BY epoch ASC;", (run_id,))
    return [dict(row) for row in cursor.fetchall()]


def save_decision(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    rationale: str
) -> None:
    """Records human decision status (ACCEPTED, REJECTED, SUPERSEDED, SELECTED) and rationale."""
    conn.execute(
        """
        INSERT INTO decisions (run_id, status, rationale)
        VALUES (?, ?, ?);
        """,
        (run_id, status, rationale)
    )
    conn.commit()


def get_decisions(conn: sqlite3.Connection, run_id: str) -> List[Dict[str, Any]]:
    """Fetches all decision rationale entries recorded for a run."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decisions WHERE run_id = ? ORDER BY timestamp DESC;", (run_id,))
    return [dict(row) for row in cursor.fetchall()]
