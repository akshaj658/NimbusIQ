from pathlib import Path

import pandas as pd

from src.utils.config import PROJECT_ROOT


def load_dataset(file_path: str) -> pd.DataFrame:
    file_path = Path(file_path)
    if not file_path.is_absolute():
        file_path = (PROJECT_ROOT / file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError(f"DataSet {file_path} is empty.")
        return df
    except Exception as exc:
        raise ValueError(f"An error occurred while loading the dataset: {exc}") from exc