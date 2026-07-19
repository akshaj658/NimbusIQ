import pandas as pd

REQUIRED_COLUMNS = [
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

NUMERIC_COLUMNS = [
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

CATEGORICAL_COLUMNS = ["Service Name", "Usage Unit", "Region/Zone"]


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and preprocess the cloud cost dataset."""
    if df is None:
        raise ValueError("Dataset cannot be None.")

    dataset = df.copy()
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataset.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    for column in dataset.select_dtypes(include=["object", "string"]).columns:
        dataset[column] = dataset[column].astype(str).str.strip()

    for column in CATEGORICAL_COLUMNS:
        if column in dataset.columns:
            dataset[column] = dataset[column].astype(str).str.strip()

    try:
        dataset["Usage Start Date"] = pd.to_datetime(dataset["Usage Start Date"], errors="coerce", format="mixed")
        dataset["Usage End Date"] = pd.to_datetime(dataset["Usage End Date"], errors="coerce", format="mixed")
    except Exception as exc:
        raise ValueError(f"Invalid date format found in dataset.\n{exc}") from exc

    if dataset[["Usage Start Date", "Usage End Date"]].isna().any().any():
        raise ValueError("Invalid or missing Usage Start Date / Usage End Date values.")

    for column in NUMERIC_COLUMNS:
        dataset[column] = pd.to_numeric(dataset[column], errors="raise")

    return dataset