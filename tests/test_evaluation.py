from src.model.train import train_model
from src.model.evaluate import evaluate_model


def main():

    dataset_path = "data/raw/gcp_final_approved_dataset.csv"

    training_result = train_model(dataset_path)

    evaluation_result = evaluate_model(training_result)

    print("✅ Model Evaluation Completed Successfully\n")

    print(f"MAE      : {evaluation_result['mae']:.2f}")

    print(f"MSE      : {evaluation_result['mse']:.2f}")

    print(f"RMSE     : {evaluation_result['rmse']:.2f}")

    print(f"R² Score : {evaluation_result['r2_score']:.4f}")


if __name__ == "__main__":
    main()