import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.preprocessing import preprocess_dataset


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    dataframe = df.copy()

    if {"Usage Start Date", "Usage End Date"}.issubset(dataframe.columns):
        dataframe["Usage Start Date"] = pd.to_datetime(dataframe["Usage Start Date"], errors="coerce")
        dataframe["Usage End Date"] = pd.to_datetime(dataframe["Usage End Date"], errors="coerce")

    if "Usage Duration (Hours)" not in dataframe.columns:
        if {"Usage Start Date", "Usage End Date"}.issubset(dataframe.columns):
            dataframe["Usage Duration (Hours)"] = (
                (dataframe["Usage End Date"] - dataframe["Usage Start Date"]).dt.total_seconds() / 3600
            )
        else:
            raise ValueError("Cannot build duration features without Usage Start/End columns.")

    if "Total Network Traffic" not in dataframe.columns:
        if {"Network Inbound Data (Bytes)", "Network Outbound Data (Bytes)"}.issubset(dataframe.columns):
            dataframe["Total Network Traffic"] = (
                dataframe["Network Inbound Data (Bytes)"] + dataframe["Network Outbound Data (Bytes)"]
            )
        else:
            raise ValueError("Cannot build network traffic features without inbound/outbound columns.")

    drop_columns = [
        column
        for column in ["Resource ID", "Usage Start Date", "Usage End Date", "Rounded Cost ($)", "Unrounded Cost ($)"]
        if column in dataframe.columns
    ]
    dataframe = dataframe.drop(columns=drop_columns, errors="ignore")

    desired_column_order = [
        "Service Name",
        "Usage Quantity",
        "Usage Unit",
        "Region/Zone",
        "CPU Utilization (%)",
        "Memory Utilization (%)",
        "Network Inbound Data (Bytes)",
        "Network Outbound Data (Bytes)",
        "Usage Duration (Hours)",
        "Total Network Traffic",
        "Cost per Quantity ($)",
        "Total Cost (INR)",
    ]

    existing = [column for column in desired_column_order if column in dataframe.columns]
    extra_columns = [column for column in dataframe.columns if column not in existing]
    return dataframe.loc[:, existing + extra_columns]


def build_preprocessor(X: pd.DataFrame):
    categorical_columns = ["Service Name", "Usage Unit", "Region/Zone"]
    numerical_columns = [column for column in X.columns if column not in categorical_columns]

    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
            ("numerical", StandardScaler(), numerical_columns),
        ]
    )


def prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    processed = preprocess_dataset(df)
    return create_features(processed)


def engineer_features(df: pd.DataFrame):
    engineered = prepare_model_frame(df)
    X = engineered.drop(columns=["Total Cost (INR)"], errors="ignore")
    y = engineered["Total Cost (INR)"]
    preprocessor = build_preprocessor(X)
    return X, y, preprocessor