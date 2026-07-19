from pathlib import Path

import pandas as pd

from src.data.loader import load_dataset
from src.data.preprocessing import preprocess_dataset
from src.data.feature_engineering import create_features
from src.model.predict import predict_cost


def test_feature_engineering_matches_prediction_input_contract():
    dataset_path = Path("data/raw/gcp_final_approved_dataset.csv")
    df = load_dataset(str(dataset_path))
    df = preprocess_dataset(df)
    sample = df.iloc[[0]].copy()

    engineered = create_features(sample)

    assert "Usage Duration (Hours)" in engineered.columns
    assert "Total Network Traffic" in engineered.columns
    assert "Total Cost (INR)" in engineered.columns
    assert engineered.shape[0] == 1

    prediction = predict_cost(sample)
    assert len(prediction) == 1
    assert prediction[0] > 0
