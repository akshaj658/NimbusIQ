"""
retrain_model.py  — retrain all model artifacts from the recreated dataset.
Run with the venv python:  .venv\Scripts\python.exe scripts\retrain_model.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model.train import train_model
from src.model.evaluate import evaluate_model

DATASET_PATH = "data/raw/gcp_final_approved_dataset.csv"

print(f"Training from: {DATASET_PATH}")
result = train_model(DATASET_PATH)

print("Training DONE")
print(f"  X_train shape : {result['X_train'].shape}")
print(f"  X_test  shape : {result['X_test'].shape}")
print(f"  Feature count : {len(result['feature_names'])}")
print()

eval_result = evaluate_model(result)
print(f"  MAE      : {eval_result['mae']:.4f}")
print(f"  RMSE     : {eval_result['rmse']:.4f}")
print(f"  R2 Score : {eval_result['r2_score']:.4f}")
print()
print("Model artifacts saved to models/")
