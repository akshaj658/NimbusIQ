"""Tests for form validation boundaries and category rejection."""
import pytest
from app.services import sanitize_form_data


def _valid_data(**overrides):
    """Return a minimally valid form payload, with overrides applied."""
    from app.blueprints.main import _get_form_options
    opts = _get_form_options()
    base = {
        "service_name": opts["service_names"][0],
        "usage_unit": opts["usage_units"][0],
        "region": opts["regions"][0],
        "usage_quantity": "10",
        "cpu": "50",
        "memory": "50",
        "network_in": "1000",
        "network_out": "1000",
        "usage_start": "2024-01-01",
        "usage_end": "2024-01-31",
        "cost_per_quantity": "0.05",
    }
    base.update(overrides)
    return base


def test_valid_form_passes_validation():
    errors, values = sanitize_form_data(_valid_data())
    assert errors == [], f"Expected no errors but got: {errors}"


def test_rejects_empty_service_name():
    errors, _ = sanitize_form_data(_valid_data(service_name=""))
    assert any("Service Name" in e for e in errors)


def test_rejects_unknown_service_name():
    errors, _ = sanitize_form_data(_valid_data(service_name="UNKNOWN_XYZ_SERVICE"))
    assert any("Service Name" in e or "Unknown" in e for e in errors)


def test_rejects_unknown_usage_unit():
    errors, _ = sanitize_form_data(_valid_data(usage_unit="FAKEUNIT"))
    assert any("Usage Unit" in e or "Unknown" in e for e in errors)


def test_rejects_unknown_region():
    errors, _ = sanitize_form_data(_valid_data(region="mars-east1"))
    assert any("Region" in e or "Unknown" in e for e in errors)


def test_rejects_cpu_above_100():
    errors, _ = sanitize_form_data(_valid_data(cpu="101"))
    assert any("CPU Utilization" in e for e in errors)


def test_rejects_cpu_below_0():
    errors, _ = sanitize_form_data(_valid_data(cpu="-1"))
    assert any("CPU Utilization" in e for e in errors)


def test_rejects_memory_above_100():
    errors, _ = sanitize_form_data(_valid_data(memory="200"))
    assert any("Memory Utilization" in e for e in errors)


def test_rejects_negative_usage_quantity():
    errors, _ = sanitize_form_data(_valid_data(usage_quantity="-5"))
    assert any("Usage Quantity" in e for e in errors)


def test_rejects_negative_network_in():
    errors, _ = sanitize_form_data(_valid_data(network_in="-100"))
    assert any("Network Inbound" in e for e in errors)


def test_rejects_negative_cost_per_quantity():
    errors, _ = sanitize_form_data(_valid_data(cost_per_quantity="-1"))
    assert any("Cost per Quantity" in e for e in errors)


def test_rejects_end_before_start():
    errors, _ = sanitize_form_data(_valid_data(usage_start="2024-06-01", usage_end="2024-01-01"))
    assert any("Usage Start Date" in e for e in errors)


def test_rejects_empty_dates():
    errors, _ = sanitize_form_data(_valid_data(usage_start="", usage_end=""))
    assert any("Start Date" in e or "End Date" in e for e in errors)


def test_rejects_non_numeric_quantity():
    errors, _ = sanitize_form_data(_valid_data(usage_quantity="abc"))
    assert any("Usage Quantity" in e for e in errors)


def test_accepts_zero_cpu():
    errors, values = sanitize_form_data(_valid_data(cpu="0"))
    assert not any("CPU" in e for e in errors)
    assert values["cpu"] == 0.0


def test_accepts_100_cpu():
    errors, values = sanitize_form_data(_valid_data(cpu="100"))
    assert not any("CPU" in e for e in errors)
    assert values["cpu"] == 100.0
