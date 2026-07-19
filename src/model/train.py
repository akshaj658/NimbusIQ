from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

from src.data.feature_engineering import engineer_features
from src.data.loader import load_dataset
from src.model.save_model import save_training_artifacts


def train_model(dataset_path: str):
    df = load_dataset(dataset_path)
    X, y, preprocessor = engineer_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    X_train = preprocessor.fit_transform(X_train)
    X_test = preprocessor.transform(X_test)
    feature_names = preprocessor.get_feature_names_out().tolist()

    model = LinearRegression()
    model.fit(X_train, y_train)

    training_result = {
        "model": model,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
    }
    save_training_artifacts(training_result)
    return training_result
