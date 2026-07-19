import os
import sqlite3
from pathlib import Path

from src.utils.config import DEFAULT_DATABASE_PATH


def get_database_path() -> Path:
    configured_path = os.environ.get("DATABASE_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path
    return DEFAULT_DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    connection = get_db_connection()
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
