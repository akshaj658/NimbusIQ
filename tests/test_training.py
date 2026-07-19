from src.model.train import train_model


def main():

    dataset_path = "data/raw/gcp_final_approved_dataset.csv"

    training_result = train_model(dataset_path)

    print("✅ Model Training Completed Successfully\n")

    print(f"Training Samples : {training_result['X_train'].shape[0]}")
    print(f"Testing Samples  : {training_result['X_test'].shape[0]}")
    print(f"Features         : {training_result['X_train'].shape[1]}")

    print("\nFirst 10 Features:\n")

    for feature in training_result["feature_names"][:10]:
        print(feature)

    print("\nModel:")
    print(training_result["model"])


if __name__ == "__main__":
    main()