import joblib
import pandas as pd

from src.data.feature_engineering import prepare_model_frame
from src.utils.config import MODEL_DIR
from src.utils.logger import logger


def load_artifacts():
    model = joblib.load(MODEL_DIR / "linear_regression.pkl")
    preprocessor = joblib.load(MODEL_DIR / "preprocessor.pkl")
    return model, preprocessor


def predict_cost(input_df: pd.DataFrame):
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
    
    clipped_predictions = []
    for prediction in predictions:
        if prediction < 0:
            logger.warning("Negative prediction detected; clipping to zero. Value=%s", prediction)
            clipped_predictions.append(0.0)
        else:
            clipped_predictions.append(float(prediction))
            
    logger.info(f"Final predictions returned: {clipped_predictions}")
    return clipped_predictions