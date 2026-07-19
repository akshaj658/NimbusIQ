import joblib

from src.utils.config import MODEL_DIR


def save_training_artifacts(training_result: dict):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(training_result["model"], MODEL_DIR / "linear_regression.pkl")
    joblib.dump(training_result["preprocessor"], MODEL_DIR / "preprocessor.pkl")
    joblib.dump(training_result["feature_names"], MODEL_DIR / "feature_names.pkl")