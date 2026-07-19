from src.data.loader import load_dataset
from src.data.preprocessing import preprocess_dataset
from src.data.feature_engineering import engineer_features


def main():

    dataset_path = "data/raw/gcp_final_approved_dataset.csv"

    # Load Dataset

    df = load_dataset(dataset_path)

    # Preprocess

    df = preprocess_dataset(df)

    # Feature Engineering

    X, y, preprocessor, feature_names = engineer_features(df)

    print("✅ Feature Engineering Completed Successfully\n")

    print(f"Feature Matrix Shape : {X.shape}")

    print(f"Target Shape         : {y.shape}")

    print("\nFirst 20 Feature Names:\n")

    for feature in feature_names[:20]:
        print(feature)

    print("\nTotal Features :", len(feature_names))

    print("\nTarget Sample:\n")

    print(y.head())


if __name__ == "__main__":
    main()