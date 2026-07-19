import pytest
import math
from app.pricing import apply_business_adjustments, compute_egress_penalty, HIGH_EGRESS_THRESHOLD_GB
from app.services import sanitize_form_data, build_input_dataframe

class TestMathematicalEdgeCases:
    def _base_values(self):
        return {
            "service_name": "Cloud Functions",
            "usage_unit": "Requests",
            "region": "us-central1",
            "usage_quantity": 2_000_000.0,
            "cpu": 10.0,
            "memory": 10.0,
            "network_in": 10.0,
            "network_out": 50.0,
            "usage_start": "2024-01-01",
            "usage_end": "2024-01-31",
            "cost_per_quantity": 0.05,
        }

    def test_free_tier_division_by_zero(self):
        """Test Case 1: The 'Free Tier' Crash Test.
        Ensures a $0 rate does not throw ZeroDivisionError and returns a 0 final cost,
        overriding the raw ML model absolute cost.
        """
        values = self._base_values()
        values["cost_per_quantity"] = 0.00
        
        # Simulating a massive raw model prediction to ensure it gets squashed
        result = apply_business_adjustments(raw_model_cost=95000.0, values=values)
        
        assert result["baseline_cost"] == 0.0
        assert result["ml_coefficient"] == 0.0
        assert result["final_cost_inr"] == 0.0

    def test_egress_singularity(self):
        """Test Case 2: The Egress Singularity.
        Ensures log domain errors (log10(0)) are avoided when network is exactly 0.
        """
        assert compute_egress_penalty(0.0) == 1.0

        values = self._base_values()
        values["network_out"] = 0.0
        
        result = apply_business_adjustments(100.0, values)
        assert result["egress_multiplier"] == 1.0

    def test_astronomical_ml_coefficient_cap(self):
        """Test Case 3: The Reasonable High-Traffic Benchmark.
        Ensures that massive model predictions are capped by MAX_ML_COEFFICIENT (5.0x).
        """
        values = self._base_values()
        # Baseline = 100 * 0.05 * 84 = 420.0
        values["usage_quantity"] = 100.0
        
        # Raw model predicts 42,000 INR (100x the baseline!)
        result = apply_business_adjustments(raw_model_cost=42000.0, values=values)
        
        assert result["ml_coefficient"] == 5.0  # Capped at 5.0x
        # 420 * 5.0 * 1.0 * 1.0 * 1.0 = 2100.0
        assert result["final_cost_inr"] == pytest.approx(2100.0)

    def test_astronomical_egress_traffic(self):
        """Test that Petabytes of traffic don't break the formula and scale reasonably via log10."""
        petabytes = 10_000_000.0 # 10 Petabytes in GB
        multiplier = compute_egress_penalty(petabytes)
        
        # 10PB is 10,000,000 GB.
        # ratio = 10,000,000 / 100 = 100,000. log10(100,000) = 5.
        # penalty = 1.0 + 0.1 * 5 = 1.5x
        assert multiplier == pytest.approx(1.5)


class TestInputSanitizationAndValidation:
    def test_mock_ui_regex_stripping(self):
        """Validates that UI suffixes like 'GB', '%', or 'bytes' are safely stripped."""
        raw_form = {
            "service_name": "Compute Engine",
            "usage_unit": "Hours",
            "region": "us-east1",
            "usage_quantity": "730.5",
            "cpu": "85%",                 # Has %
            "memory": "  91 %  ",         # Has spaces and %
            "network_in": "150 GB",       # Has GB
            "network_out": "350 bytes",   # Has bytes
            "usage_start": "2024-01-01",
            "usage_end": "2024-01-31",
            "cost_per_quantity": "$0.12", # Has $
        }
        
        # Assuming sanitize_form_data strips these correctly
        errors, values = sanitize_form_data(raw_form)
        
        assert not errors
        assert values["cpu"] == 85.0
        assert values["memory"] == 91.0
        assert values["network_in"] == 150.0
        assert values["network_out"] == 350.0
        assert values["cost_per_quantity"] == 0.12
