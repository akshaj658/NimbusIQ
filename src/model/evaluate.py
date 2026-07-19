"""
src/model/evaluate.py
=====================
Computes model performance metrics (MAE, MSE, RMSE, R-squared) against holdout datasets.
"""
from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_model(training_result: dict[str, Any]) -> dict[str, Any]:
    """Evaluates the trained model performance against test datasets.

    Args:
        training_result: Dictionary containing model, test inputs, and target variables.

    Returns:
        Dictionary containing metric names mapped to evaluated scores.
    """
    model = training_result["model"]
    X_test = training_result["X_test"]
    y_test = training_result["y_test"]

    predictions = model.predict(X_test)
    mae: float = float(mean_absolute_error(y_test, predictions))
    mse: float = float(mean_squared_error(y_test, predictions))
    rmse: float = float(np.sqrt(mse))
    r2: float = float(r2_score(y_test, predictions))

    return {
        "predictions": predictions,
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2_score": r2,
    }