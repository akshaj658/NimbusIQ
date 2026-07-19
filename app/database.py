"""
app/database.py
===============
Manages database path resolution, initialization, and connection pooling for StadiumIQ history logs.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from src.utils.config import DEFAULT_DATABASE_PATH, PROJECT_ROOT


def get_database_path() -> Path:
    """Resolves and returns the database absolute file path from environment or defaults.

    Returns:
        The absolute Path to the SQLite database file.
    """
    configured_path: str | None = os.environ.get("DATABASE_PATH")
    if configured_path:
        path: Path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path
    return DEFAULT_DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    """Establishes and returns a connection to the SQLite database.

    Returns:
        A sqlite3.Connection with Row row_factory configured.
    """
    database_path: Path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection: sqlite3.Connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Initializes the database schema and structures if the table does not exist."""
    connection: sqlite3.Connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            service_name TEXT NOT NULL,
            usage_quantity REAL NOT NULL,
            usage_unit TEXT NOT NULL,
            region TEXT NOT NULL,
            cpu REAL NOT NULL,
            memory REAL NOT NULL,
            network_in REAL NOT NULL,
            network_out REAL NOT NULL,
            usage_start TEXT NOT NULL,
            usage_end TEXT NOT NULL,
            cost_per_quantity REAL NOT NULL,
            predicted_cost REAL NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()
