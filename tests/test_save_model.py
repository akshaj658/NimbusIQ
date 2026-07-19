from src.model.train import train_model
from src.model.save_model import save_training_artifacts


def main():

    dataset_path = "data/raw/gcp_final_approved_dataset.csv"

    training_result = train_model(dataset_path)

    save_training_artifacts(training_result)

    print("Model Saved Successfully")


if __name__ == "__main__":
    main()