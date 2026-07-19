"""
src/data/loader.py
==================
Utility module for loading data files into Pandas DataFrames.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
from src.utils.config import PROJECT_ROOT


def load_dataset(file_path: str | Path) -> pd.DataFrame:
    """Loads a CSV dataset from a given path and resolves relative paths to the PROJECT_ROOT.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        The loaded pandas DataFrame.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        ValueError: If dataset is empty or fails to parse.
    """
    resolved_path: Path = Path(file_path)
    if not resolved_path.is_absolute():
        resolved_path = (PROJECT_ROOT / resolved_path).resolve()

    if not resolved_path.exists():
        raise FileNotFoundError(f"The file {resolved_path} does not exist.")

    try:
        df: pd.DataFrame = pd.read_csv(resolved_path)
        if df.empty:
            raise ValueError(f"DataSet {resolved_path} is empty.")
        return df
    except Exception as exc:
        raise ValueError(f"An error occurred while loading the dataset: {exc}") from exc