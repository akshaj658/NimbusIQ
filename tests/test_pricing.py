"""Tests for app/pricing.py — business adjustment engine."""
import math
import pytest
from app.pricing import (
    get_regional_multiplier,
    compute_egress_penalty,
    compute_workload_density_multiplier,
    apply_business_adjustments,
    HIGH_EGRESS_THRESHOLD_GB,
    WORKLOAD_CPU_THRESHOLD,
    WORKLOAD_MEM_THRESHOLD,
)


# ---------------------------------------------------------------------------
# 1. Regional Multiplier
# ---------------------------------------------------------------------------

class TestRegionalMultiplier:
    def test_us_central1_is_baseline(self):
        assert get_regional_multiplier("us-central1") == 1.000

    def test_europe_west6_premium(self):
        assert get_regional_multiplier("europe-west6") == 1.100

    def test_asia_east2_premium(self):
        assert get_regional_multiplier("asia-east2") == 1.130

    def test_southamerica_premium(self):
        assert get_regional_multiplier("southamerica-east1") == 1.180

    def test_me_central2_premium(self):
        assert get_regional_multiplier("me-central2") == 1.220

    def test_case_insensitive(self):
        assert get_regional_multiplier("US-CENTRAL1") == get_regional_multiplier("us-central1")

    def test_unknown_region_gets_default_conservative(self):
        mult = get_regional_multiplier("mars-north1")
        assert mult == 1.05

    def test_all_multipliers_are_gte_1(self):
        from app.pricing import REGIONAL_MULTIPLIERS
        for region, mult in REGIONAL_MULTIPLIERS.items():
            assert mult >= 1.0, f"Region {region} has multiplier < 1.0"


# ---------------------------------------------------------------------------
# 2. Egress Penalty
# ---------------------------------------------------------------------------

class TestEgressPenalty:
    def test_no_penalty_below_threshold(self):
        assert compute_egress_penalty(0) == 1.0
        assert compute_egress_penalty(10) == 1.0   # 10 GB

    def test_no_penalty_at_threshold(self):
        assert compute_egress_penalty(HIGH_EGRESS_THRESHOLD_GB) == 1.0  # exactly 100 GB

    def test_penalty_at_1tb(self):
        # 1 TB = 1000 GB = 10 × threshold → log10(10) = 1 → penalty = 1 + 0.1*1 = 1.1
        result = compute_egress_penalty(1000)
        assert abs(result - 1.1) < 1e-9

    def test_penalty_at_10tb(self):
        # 10 TB = 10000 GB = 100 × threshold → log10(100) = 2 → penalty = 1 + 0.1*2 = 1.2
        result = compute_egress_penalty(10000)
        assert abs(result - 1.2) < 1e-9

    def test_penalty_is_monotonically_increasing(self):
        sizes = [100, 500, 1000, 10000, 100000]
        penalties = [compute_egress_penalty(s) for s in sizes]
        assert penalties == sorted(penalties)

    def test_penalty_never_below_1(self):
        for size in [0, 1, 10, 100, 10000]:
            assert compute_egress_penalty(size) >= 1.0


# ---------------------------------------------------------------------------
# 3. Workload Density Multiplier
# ---------------------------------------------------------------------------

class TestWorkloadDensityMultiplier:
    def test_no_multiplier_when_both_below_threshold(self):
        assert compute_workload_density_multiplier(50, 50) == 1.0

    def test_no_multiplier_when_only_cpu_above(self):
        assert compute_workload_density_multiplier(80, 30) == 1.0

    def test_no_multiplier_when_only_memory_above(self):
        assert compute_workload_density_multiplier(30, 80) == 1.0

    def test_no_multiplier_at_threshold_exactly(self):
        assert compute_workload_density_multiplier(60.0, 60.0) == 1.0

    def test_multiplier_at_100_100(self):
        result = compute_workload_density_multiplier(100, 100)
        assert abs(result - 1.225) < 1e-9

    def test_multiplier_at_80_80(self):
        # cpu_excess = (80-60)/(100-60) = 0.5
        # mem_excess = 0.5
        # mult = 1 + 0.225 * 0.5 * 0.5 = 1.05625
        result = compute_workload_density_multiplier(80, 80)
        assert abs(result - 1.05625) < 1e-9

    def test_multiplier_always_gte_1(self):
        for cpu in range(0, 101, 10):
            for mem in range(0, 101, 10):
                assert compute_workload_density_multiplier(cpu, mem) >= 1.0


# ---------------------------------------------------------------------------
# 4. apply_business_adjustments (integration)
# ---------------------------------------------------------------------------

class TestApplyBusinessAdjustments:
    def _values(self, **overrides):
        base = {
            "service_name": "Cloud Run",
            "usage_quantity": 100.0,
            "usage_unit": "Hours",
            "region": "us-central1",
            "cpu": 50.0,
            "memory": 50.0,
            "network_in": 10.0,
            "network_out": 10.0,     # 10 GB (well below 100 GB)
            "usage_start": "2024-01-01",
            "usage_end": "2024-01-31",
            "cost_per_quantity": 0.05,
        }
        base.update(overrides)
        return base

    def test_baseline_cost_is_qty_times_rate_times_usd_inr(self, monkeypatch):
        monkeypatch.setenv("USD_TO_INR_RATE", "84.0")
        # ML model prediction = 500.0 (INR)
        result = apply_business_adjustments(500.0, self._values())
        expected_baseline_inr = 100.0 * 0.05 * 84.0 # 420.0
        assert result["baseline_cost"] == pytest.approx(expected_baseline_inr)
        # ml_coefficient is rounded to 4 decimals in the code
        assert result["ml_coefficient"] == pytest.approx(500.0 / expected_baseline_inr, abs=1e-4)

    def test_no_adjustments_for_us_central_low_load(self):
        result = apply_business_adjustments(500.0, self._values())
        # regional=1.0, egress=1.0, workload=1.0 → final_cost == raw_model_cost
        assert result["regional_multiplier"] == 1.0
        assert result["egress_multiplier"] == 1.0
        assert result["workload_multiplier"] == 1.0
        assert result["total_multiplier"] == 1.0
        assert result["final_cost_inr"] == pytest.approx(500.0)

    def test_europe_premium_applied(self):
        result = apply_business_adjustments(1000.0, self._values(region="europe-west6"))
        assert result["regional_multiplier"] == 1.10
        assert result["final_cost_inr"] == pytest.approx(1000.0 * 1.10, abs=0.01)

    def test_high_egress_penalty_applied(self):
        result = apply_business_adjustments(1000.0, self._values(network_out=1000))  # 1 TB (1000 GB)
        assert result["egress_multiplier"] == pytest.approx(1.1, abs=1e-9)
        assert result["final_cost_inr"] == pytest.approx(1000.0 * 1.0 * 1.1 * 1.0, abs=0.01)

    def test_workload_density_applied(self):
        result = apply_business_adjustments(1000.0, self._values(cpu=100.0, memory=100.0))
        assert result["workload_multiplier"] == pytest.approx(1.225, abs=1e-9)
        assert result["final_cost_inr"] == pytest.approx(1000.0 * 1.225, abs=0.01)

    def test_combined_multipliers(self):
        result = apply_business_adjustments(
            1000.0,
            self._values(region="europe-west6", network_out=1000, cpu=100, memory=100)
        )
        expected = 1000.0 * 1.10 * 1.1 * 1.225
        assert result["final_cost_inr"] == pytest.approx(expected, abs=0.01)

    def test_breakdown_keys_present(self):
        result = apply_business_adjustments(100.0, self._values())
        required_keys = {
            "baseline_cost", "ml_coefficient", "regional_multiplier",
            "egress_multiplier", "workload_multiplier", "total_multiplier",
            "final_cost_inr"
        }
        assert required_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# 5. _strip_non_numeric (unit tests)
# ---------------------------------------------------------------------------

class TestStripNonNumeric:
    def test_strips_percent(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("64%") == "64"

    def test_strips_gb_suffix(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("1.5 GB") == "1.5"

    def test_strips_bytes_suffix(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("1024 bytes") == "1024"

    def test_strips_spaces(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("  50  ") == "50"

    def test_preserves_minus(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("-1") == "-1"

    def test_preserves_decimal(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("0.05") == "0.05"

    def test_strips_mixed(self):
        from app.services import _strip_non_numeric
        assert _strip_non_numeric("100.5%") == "100.5"


# ---------------------------------------------------------------------------
# 6. sanitize_form_data accepts unit-suffixed inputs
# ---------------------------------------------------------------------------

class TestSanitizeWithSuffixes:
    def _base_valid_data(self):
        from app.blueprints.main import _get_form_options
        opts = _get_form_options()
        return {
            "service_name": opts["service_names"][0],
            "usage_unit": opts["usage_units"][0],
            "region": opts["regions"][0],
            "usage_quantity": "100",
            "cpu": "50",
            "memory": "50",
            "network_in": "1000",
            "network_out": "1000",
            "usage_start": "2024-01-01",
            "usage_end": "2024-01-31",
            "cost_per_quantity": "0.05",
        }

    def test_cpu_with_percent_sign(self):
        from app.services import sanitize_form_data
        data = self._base_valid_data()
        data["cpu"] = "64%"
        errors, values = sanitize_form_data(data)
        assert not any("CPU" in e for e in errors)
        assert values["cpu"] == 64.0

    def test_network_with_bytes_label(self):
        from app.services import sanitize_form_data
        data = self._base_valid_data()
        data["network_in"] = "1024 bytes"
        errors, values = sanitize_form_data(data)
        assert not any("Network Inbound" in e for e in errors)
        assert values["network_in"] == 1024.0

    def test_memory_with_gb_suffix(self):
        from app.services import sanitize_form_data
        data = self._base_valid_data()
        data["memory"] = "32 GB"
        errors, values = sanitize_form_data(data)
        # 32 GB as percentage is still 32.0 (user's responsibility for input)
        assert values["memory"] == 32.0
