from src.data.loader import load_dataset
from src.data.preprocessing import preprocess_dataset


def main():

    dataset_path = "data/raw/gcp_final_approved_dataset.csv"

    df = load_dataset(dataset_path)

    processed_df = preprocess_dataset(df)

    print("\n✅ Preprocessing completed successfully.\n")

    print(f"Shape : {processed_df.shape}")

    print("\nData Types:")
    print(processed_df.dtypes)

    print("\nMissing Values:")
    print(processed_df.isnull().sum())

    print("\nFirst 5 Rows:")
    print(processed_df.head())


if __name__ == "__main__":
    main()