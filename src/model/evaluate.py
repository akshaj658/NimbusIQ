import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_model(training_result: dict):
    model = training_result["model"]
    X_test = training_result["X_test"]
    y_test = training_result["y_test"]

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    mse = mean_squared_error(y_test, predictions)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, predictions)

    return {
        "predictions": predictions,
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2_score": r2,
    }