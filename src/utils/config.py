"""
src/utils/config.py
===================
Configuration constants for the StadiumIQ application directories and database paths.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_PATH: Path = PROJECT_ROOT / "data" / "raw"
MODEL_DIR: Path = PROJECT_ROOT / "models"
DEFAULT_DATABASE_PATH: Path = PROJECT_ROOT / "cloudcostai.db"
