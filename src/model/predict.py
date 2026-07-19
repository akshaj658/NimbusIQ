"""
src/model/predict.py
===================
Uses trained Linear Regression model artifacts to predict costs based on engineered input features.
"""
from __future__ import annotations

from typing import Any
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.compose import ColumnTransformer

from src.data.feature_engineering import prepare_model_frame
from src.utils.config import MODEL_DIR
from src.utils.logger import logger


def load_artifacts() -> tuple[LinearRegression, ColumnTransformer]:
    """Loads linear regression model and preprocessor artifacts from storage.

    Returns:
        A tuple of (LinearRegression, ColumnTransformer).
    """
    model: LinearRegression = joblib.load(MODEL_DIR / "linear_regression.pkl")
    preprocessor: ColumnTransformer = joblib.load(MODEL_DIR / "preprocessor.pkl")
    return model, preprocessor


def predict_cost(input_df: pd.DataFrame) -> list[float]:
    """Prepares features and predicts operational costs using the model pipeline.

    Args:
        input_df: The raw input DataFrame containing operational data.

    Returns:
        List of clipped non-negative cost predictions.
    """
    logger.info("Starting prediction trace.")
    logger.info(f"Input DataFrame:\n{input_df}")
    
    model, preprocessor = load_artifacts()
    logger.info("Loaded artifacts successfully.")
    
    prepared_frame = prepare_model_frame(input_df)
    logger.info(f"Feature Engineering completed.\nPrepared DataFrame:\n{prepared_frame}")
    
    X = prepared_frame.drop(columns=["Total Cost (INR)"], errors="ignore")
    X_processed = preprocessor.transform(X)
    logger.info(f"Preprocessor transformed shape: {X_processed.shape}")
    
    predictions = model.predict(X_processed)
    logger.info(f"Model raw predictions: {predictions}")
    
    clipped_predictions: list[float] = []
    for pred in predictions:
        val = float(pred)
        if val < 0.0:
            logger.warning("Negative prediction detected; clipping to zero. Value=%s", val)
            clipped_predictions.append(0.0)
        else:
            clipped_predictions.append(val)
            
    logger.info(f"Final predictions returned: {clipped_predictions}")
    return clipped_predictions