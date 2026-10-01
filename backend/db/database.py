"""
traintrace/backend/db/database.py
=================================
Embedded SQLite Connection Manager and Relational Schema Initializer.
"""

import sqlite3
from typing import Generator
from config import DB_PATH, DATABASE_DIR


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes SQLite connection with dictionary row access and WAL mode enabled.
    """
    # Ensure database parent directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    
    # Enables column access by name (e.g. row["status"]) instead of numeric tuples
    conn.row_factory = sqlite3.Row
    
    # Enable Foreign Keys enforcement in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Enable Write-Ahead Logging (WAL) for fast concurrent REST API reads
    conn.execute("PRAGMA journal_mode = WAL;")
    
    return conn


def init_db() -> None:
    """
    Initializes database tables if they do not exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Experiments Parent Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        objective TEXT NOT NULL,
        target_accuracy REAL,
        target_latency_ms REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Executed Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        approach_name TEXT NOT NULL,
        model_architecture TEXT NOT NULL,
        batch_size INTEGER NOT NULL,
        epochs INTEGER NOT NULL,
        learning_rate REAL NOT NULL,
        seed INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'QUEUED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
    );
    """)
    
    # 3. Epoch Metrics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS epoch_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        epoch INTEGER NOT NULL,
        train_loss REAL NOT NULL,
        train_acc REAL NOT NULL,
        val_loss REAL NOT NULL,
        val_acc REAL NOT NULL,
        epoch_time_sec REAL NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
    );
    """)
    
    # 4. Decision Traceability Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        status TEXT NOT NULL,
        rationale TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
    );
    """)
    
    # 5. Model Registry Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        run_id TEXT NOT NULL,
        checkpoint_path TEXT NOT NULL,
        test_accuracy REAL,
        latency_ms REAL,
        status TEXT NOT NULL DEFAULT 'CANDIDATE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)
    
    conn.commit()
    conn.close()
