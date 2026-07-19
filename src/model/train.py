"""
src/model/train.py
==================
Orchestrates model training by loading, preprocessing, and fitting a linear regression pipeline.
"""
from __future__ import annotations

from typing import Any
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

from src.data.feature_engineering import engineer_features
from src.data.loader import load_dataset
from src.model.save_model import save_training_artifacts


def train_model(dataset_path: str) -> dict[str, Any]:
    """Loads dataset, engineers features, trains the model, and persists training artifacts.

    Args:
        dataset_path: Path to the raw dataset CSV file.

    Returns:
        A dictionary containing training inputs, outputs, models, and preprocessors.
    """
    df = load_dataset(dataset_path)
    X, y, preprocessor = engineer_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    feature_names: list[str] = preprocessor.get_feature_names_out().tolist()

    model = LinearRegression()
    model.fit(X_train_processed, y_train)

    training_result: dict[str, Any] = {
        "model": model,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "X_train": X_train_processed,
        "X_test": X_test_processed,
        "y_train": y_train,
        "y_test": y_test,
    }
    save_training_artifacts(training_result)
    return training_result
