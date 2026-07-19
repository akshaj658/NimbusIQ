"""
src/data/preprocessing.py
=========================
Validates, cleans, and pre-processes raw datasets for model training or predictions.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS: list[str] = [
    "Resource ID",
    "Service Name",
    "Usage Quantity",
    "Usage Unit",
    "Region/Zone",
    "CPU Utilization (%)",
    "Memory Utilization (%)",
    "Network Inbound Data (Bytes)",
    "Network Outbound Data (Bytes)",
    "Usage Start Date",
    "Usage End Date",
    "Cost per Quantity ($)",
    "Unrounded Cost ($)",
    "Rounded Cost ($)",
    "Total Cost (INR)",
]

NUMERIC_COLUMNS: list[str] = [
    "Usage Quantity",
    "CPU Utilization (%)",
    "Memory Utilization (%)",
    "Network Inbound Data (Bytes)",
    "Network Outbound Data (Bytes)",
    "Cost per Quantity ($)",
    "Unrounded Cost ($)",
    "Rounded Cost ($)",
    "Total Cost (INR)",
]

CATEGORICAL_COLUMNS: list[str] = ["Service Name", "Usage Unit", "Region/Zone"]


def preprocess_dataset(df: pd.DataFrame | None) -> pd.DataFrame:
    """Validates and pre-processes input DataFrames for features engineering or model consumption.

    Args:
        df: The pandas DataFrame representing the dataset.

    Returns:
        The preprocessed and validated pandas DataFrame.

    Raises:
        ValueError: If dataset is None, missing required columns, has invalid dates,
                    or non-numeric data types where numeric are required.
    """
    if df is None:
        raise ValueError("Dataset cannot be None.")

    dataset: pd.DataFrame = df.copy()
    missing_columns: list[str] = [col for col in REQUIRED_COLUMNS if col not in dataset.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Standardize string fields by stripping whitespace
    for column in dataset.select_dtypes(include=["object", "string", "category"]).columns:
        dataset[column] = dataset[column].astype(str).str.strip()

    # Parse date columns
    try:
        dataset["Usage Start Date"] = pd.to_datetime(dataset["Usage Start Date"], errors="coerce", format="mixed")
        dataset["Usage End Date"] = pd.to_datetime(dataset["Usage End Date"], errors="coerce", format="mixed")
    except Exception as exc:
        raise ValueError(f"Invalid date format found in dataset.\n{exc}") from exc

    if dataset[["Usage Start Date", "Usage End Date"]].isna().any().any():
        raise ValueError("Invalid or missing Usage Start Date / Usage End Date values.")

    # Cast numeric columns strictly
    for column in NUMERIC_COLUMNS:
        dataset[column] = pd.to_numeric(dataset[column], errors="raise")

    return dataset