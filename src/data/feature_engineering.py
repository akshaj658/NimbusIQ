"""
src/data/feature_engineering.py
==============================
Handles feature extraction, scaling, and preparation of data for prediction or training pipelines.
"""
from __future__ import annotations

from typing import Any
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.preprocessing import preprocess_dataset

# Column constants to avoid repeated literals
COL_START_DATE: str = "Usage Start Date"
COL_END_DATE: str = "Usage End Date"
COL_DURATION: str = "Usage Duration (Hours)"
COL_NET_IN: str = "Network Inbound Data (Bytes)"
COL_NET_OUT: str = "Network Outbound Data (Bytes)"
COL_NET_TOTAL: str = "Total Network Traffic"
COL_COST_INR: str = "Total Cost (INR)"

CATEGORICAL_COLUMNS: list[str] = ["Service Name", "Usage Unit", "Region/Zone"]

DESIRED_COLUMN_ORDER: list[str] = [
    "Service Name",
    "Usage Quantity",
    "Usage Unit",
    "Region/Zone",
    "CPU Utilization (%)",
    "Memory Utilization (%)",
    "Network Inbound Data (Bytes)",
    "Network Outbound Data (Bytes)",
    COL_DURATION,
    COL_NET_TOTAL,
    "Cost per Quantity ($)",
    COL_COST_INR,
]

COLUMNS_TO_DROP: list[str] = [
    "Resource ID",
    COL_START_DATE,
    COL_END_DATE,
    "Rounded Cost ($)",
    "Unrounded Cost ($)",
]


def _add_duration_feature(df: pd.DataFrame) -> None:
    """Calculates and populates the Usage Duration (Hours) column in place."""
    if COL_DURATION in df.columns:
        return

    if {COL_START_DATE, COL_END_DATE}.issubset(df.columns):
        df[COL_START_DATE] = pd.to_datetime(df[COL_START_DATE], errors="coerce")
        df[COL_END_DATE] = pd.to_datetime(df[COL_END_DATE], errors="coerce")
        df[COL_DURATION] = (df[COL_END_DATE] - df[COL_START_DATE]).dt.total_seconds() / 3600.0
    else:
        raise ValueError(f"Cannot build duration features without {COL_START_DATE} and {COL_END_DATE} columns.")


def _add_network_feature(df: pd.DataFrame) -> None:
    """Calculates and populates the Total Network Traffic column in-place."""
    if COL_NET_TOTAL in df.columns:
        return

    if {COL_NET_IN, COL_NET_OUT}.issubset(df.columns):
        df[COL_NET_TOTAL] = df[COL_NET_IN] + df[COL_NET_OUT]
    else:
        raise ValueError(f"Cannot build network traffic features without {COL_NET_IN} and {COL_NET_OUT} columns.")


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Constructs model features from raw preprocess output.

    Args:
        df: Input pandas DataFrame.

    Returns:
        DataFrame containing engineered columns in standardized order.
    """
    dataframe: pd.DataFrame = df.copy()

    # Apply feature calculations
    _add_duration_feature(dataframe)
    _add_network_feature(dataframe)

    # Drop administrative and raw date columns
    drop_columns = [col for col in COLUMNS_TO_DROP if col in dataframe.columns]
    dataframe = dataframe.drop(columns=drop_columns, errors="ignore")

    # Order columns predictably
    existing_cols = [col for col in DESIRED_COLUMN_ORDER if col in dataframe.columns]
    extra_cols = [col for col in dataframe.columns if col not in existing_cols]
    return dataframe.loc[:, existing_cols + extra_cols]


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Constructs the ColumnTransformer for categorical and numerical features.

    Args:
        X: The model inputs design matrix.

    Returns:
        Fitted or unfitted preprocessor ColumnTransformer.
    """
    numerical_columns = [column for column in X.columns if column not in CATEGORICAL_COLUMNS]

    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
            ("numerical", StandardScaler(), numerical_columns),
        ]
    )


def prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Wrapper that pre-processes and engineers features.

    Args:
        df: Input raw pandas DataFrame.

    Returns:
        Engineered pandas DataFrame.
    """
    processed = preprocess_dataset(df)
    return create_features(processed)


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, ColumnTransformer]:
    """Generates X, y datasets and the associated preprocessor transformer.

    Args:
        df: Raw input DataFrame.

    Returns:
        A tuple of (X, y, preprocessor).
    """
    engineered = prepare_model_frame(df)
    X = engineered.drop(columns=[COL_COST_INR], errors="ignore")
    y = engineered[COL_COST_INR]
    preprocessor = build_preprocessor(X)
    return X, y, preprocessor