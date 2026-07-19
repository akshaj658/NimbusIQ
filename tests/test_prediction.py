from src.data.loader import load_dataset
from src.data.preprocessing import preprocess_dataset
from src.model.predict import predict_cost
from app.services import sanitize_form_data


def test_predictions_are_non_negative_for_dataset_samples():
    df = load_dataset("data/raw/gcp_final_approved_dataset.csv")
    df = preprocess_dataset(df)

    for index in range(min(20, len(df))):
        sample = df.iloc[[index]].copy()
        prediction = predict_cost(sample)[0]
        assert prediction >= 0


def test_form_validation_rejects_invalid_ranges():
    errors, _ = sanitize_form_data(
        {
            "service_name": "Cloud Run",
            "usage_quantity": "5",
            "usage_unit": "Hours",
            "region": "us-central1",
            "cpu": "-1",
            "memory": "110",
            "network_in": "100",
            "network_out": "100",
            "usage_start": "2024-08-01",
            "usage_end": "2024-07-31",
            "cost_per_quantity": "3",
        }
    )

    assert any("CPU Utilization" in error for error in errors)
    assert any("Memory Utilization" in error for error in errors)
    assert any("Usage Start Date" in error for error in errors)


def main():

    df = load_dataset("data/raw/gcp_final_approved_dataset.csv")

    df = preprocess_dataset(df)

    sample = df.iloc[[0]].copy()

    actual_cost = sample["Total Cost (INR)"].iloc[0]

    prediction = predict_cost(sample)

    print("\nPrediction Test\n")

    print(f"Actual Cost    : ₹{actual_cost:,.2f}")

    print(f"Predicted Cost : ₹{prediction[0]:,.2f}")

    print(f"Difference     : ₹{abs(actual_cost - prediction[0]):,.2f}")


if __name__ == "__main__":
    main()