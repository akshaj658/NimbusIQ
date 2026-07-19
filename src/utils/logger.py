"""
src/utils/logger.py
===================
Logging configuration helper for StadiumIQ system processes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from src.utils.config import PROJECT_ROOT

LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def configure_logging() -> logging.Logger:
    """Configures the standard application logger to output to both console and log files.

    Returns:
        The configured logging.Logger instance.
    """
    app_logger = logging.getLogger("stadiumiq")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    if not app_logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        
        file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        
        app_logger.addHandler(file_handler)
        app_logger.addHandler(stream_handler)

    return app_logger


logger: logging.Logger = configure_logging()
