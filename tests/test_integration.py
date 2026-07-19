"""Integration tests: Homepage -> Predict -> History -> Delete pipeline."""
import os
import tempfile
import pytest

# Use a temp DB for tests to avoid polluting production data
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), "cloudcostai_test.db")


@pytest.fixture(scope="module")
def client():
    from app.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["DATABASE_PATH"] = os.environ["DATABASE_PATH"]
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


# ------------------------------------------------------------------
# 1. Homepage
# ------------------------------------------------------------------
def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CloudCostAI" in response.data


def test_homepage_contains_form(client):
    response = client.get("/")
    assert b"prediction-form" in response.data
    assert b"service_name" in response.data
    assert b"usage_unit" in response.data
    assert b"region" in response.data


def test_homepage_dropdowns_populated(client):
    """Dropdowns must contain at least one option beyond the placeholder."""
    response = client.get("/")
    assert b"<option value=" in response.data


# ------------------------------------------------------------------
# 2. Form Options API
# ------------------------------------------------------------------
def test_form_options_api_returns_lists(client):
    response = client.get("/api/form-options")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data.get("service_names"), list)
    assert isinstance(data.get("usage_units"), list)
    assert isinstance(data.get("regions"), list)
    assert len(data["service_names"]) > 0
    assert len(data["usage_units"]) > 0
    assert len(data["regions"]) > 0


# ------------------------------------------------------------------
# 3. Prediction with invalid data -> validation errors
# ------------------------------------------------------------------
def test_predict_rejects_empty_form(client):
    response = client.post("/predict", data={})
    assert response.status_code == 200
    # Should get flash error messages
    assert b"required" in response.data.lower()


def test_predict_rejects_unknown_service(client):
    response = client.post("/predict", data={
        "service_name": "TOTALLY_FAKE_SERVICE_XYZ",
        "usage_unit": "Hours",
        "region": "us-central1",
        "usage_quantity": "10",
        "cpu": "50",
        "memory": "50",
        "network_in": "1000",
        "network_out": "1000",
        "usage_start": "2024-01-01",
        "usage_end": "2024-01-31",
        "cost_per_quantity": "0.05",
    })
    assert response.status_code == 200
    assert b"Unknown Service Name" in response.data or b"unknown" in response.data.lower()


def test_predict_rejects_cpu_out_of_range(client):
    response = client.post("/predict", data={
        "service_name": "Cloud Run",
        "usage_unit": "Hours",
        "region": "us-central1",
        "usage_quantity": "10",
        "cpu": "150",  # Invalid: > 100
        "memory": "50",
        "network_in": "1000",
        "network_out": "1000",
        "usage_start": "2024-01-01",
        "usage_end": "2024-01-31",
        "cost_per_quantity": "0.05",
    })
    assert response.status_code == 200
    assert b"CPU Utilization" in response.data


def test_predict_rejects_end_before_start(client):
    response = client.post("/predict", data={
        "service_name": "Cloud Run",
        "usage_unit": "Hours",
        "region": "us-central1",
        "usage_quantity": "10",
        "cpu": "50",
        "memory": "50",
        "network_in": "1000",
        "network_out": "1000",
        "usage_start": "2024-06-01",
        "usage_end": "2024-01-01",   # Before start
        "cost_per_quantity": "0.05",
    })
    assert response.status_code == 200
    assert b"Usage Start Date" in response.data


def test_predict_rejects_negative_network(client):
    response = client.post("/predict", data={
        "service_name": "Cloud Run",
        "usage_unit": "Hours",
        "region": "us-central1",
        "usage_quantity": "10",
        "cpu": "50",
        "memory": "50",
        "network_in": "-500",   # Invalid
        "network_out": "1000",
        "usage_start": "2024-01-01",
        "usage_end": "2024-01-31",
        "cost_per_quantity": "0.05",
    })
    assert response.status_code == 200
    assert b"Network Inbound" in response.data


# ------------------------------------------------------------------
# 4. History API
# ------------------------------------------------------------------
def test_history_api_returns_json(client):
    response = client.get("/history")
    assert response.status_code == 200
    data = response.get_json()
    assert "predictions" in data
    assert isinstance(data["predictions"], list)


def test_history_api_search_filter(client):
    response = client.get("/history?q=CloudRun")
    assert response.status_code == 200
    data = response.get_json()
    assert "predictions" in data
