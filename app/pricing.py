"""
app/pricing.py — StadiumIQ Post-Model Operational Cost Calibration Engine

Applies deterministic business rules on top of the raw ML model output to
produce accurate stadium operational cost estimates for FIFA World Cup 2026.
Does NOT alter model training or the underlying regression pipeline.

Calibration pipeline:
  raw_model_cost (INR, from model.predict)
  → Venue-Based Regional Calibration Multiplier
  → High Fan-Egress / Network Load Penalty
  → High-Utilisation (Crowd Density) Surcharge
  → INR Rate Adjustment (env-configurable)
  = final_cost_inr
"""
from __future__ import annotations

import math
import os
from typing import Any

# ---------------------------------------------------------------------------
# Venue-based calibration multipliers (relative to US-central1 baseline = 1.00)
# Models cost premiums across FIFA World Cup 2026 host stadium regions.
# ---------------------------------------------------------------------------
REGIONAL_MULTIPLIERS: dict[str, float] = {
    # United States (baseline)
    "us-central1":              1.000,
    "us-east1":                 1.000,
    "us-east4":                 1.020,
    "us-east5":                 1.020,
    "us-west1":                 1.010,
    "us-west2":                 1.030,
    "us-west3":                 1.030,
    "us-west4":                 1.030,
    "us-south1":                1.025,
    # Canada
    "northamerica-northeast1":  1.040,
    "northamerica-northeast2":  1.040,
    # Europe
    "europe-west1":             1.060,
    "europe-west2":             1.080,
    "europe-west3":             1.080,
    "europe-west4":             1.060,
    "europe-west6":             1.100,
    "europe-west8":             1.070,
    "europe-west9":             1.070,
    "europe-west10":            1.090,
    "europe-west12":            1.090,
    "europe-central2":          1.080,
    "europe-north1":            1.070,
    "europe-southwest1":        1.070,
    # Asia Pacific
    "asia-east1":               1.100,
    "asia-east2":               1.130,
    "asia-northeast1":          1.120,
    "asia-northeast2":          1.120,
    "asia-northeast3":          1.130,
    "asia-south1":              1.090,
    "asia-south2":              1.090,
    "asia-southeast1":          1.100,
    "asia-southeast2":          1.110,
    "australia-southeast1":     1.140,
    "australia-southeast2":     1.140,
    # South America
    "southamerica-east1":       1.180,
    "southamerica-west1":       1.180,
    # Middle East & Africa
    "me-west1":                 1.200,
    "me-central1":              1.200,
    "me-central2":              1.220,
    "africa-south1":            1.220,
}

# Fallback for any region not in the map above (conservative premium)
_DEFAULT_REGIONAL_MULTIPLIER: float = 1.05

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
HIGH_EGRESS_THRESHOLD_GB:    float = 100.0  # 100 GB
WORKLOAD_CPU_THRESHOLD:      float = 60.0   # percent
WORKLOAD_MEM_THRESHOLD:      float = 60.0   # percent


# ---------------------------------------------------------------------------
# Individual multiplier functions (each independently testable)
# ---------------------------------------------------------------------------

def get_regional_multiplier(region: str) -> float:
    """Return the price premium multiplier for a given GCP region/zone.

    Performs a case-insensitive lookup. Unknown regions get a small
    conservative premium of 1.05x.
    """
    return REGIONAL_MULTIPLIERS.get(region.strip().lower(), _DEFAULT_REGIONAL_MULTIPLIER)


def compute_egress_penalty(network_out_gb: float) -> float:
    """Exponential egress penalty for high outbound traffic.

    Activates only when network_out_gb > 100 GB.
    Uses log10 scaling so the penalty grows meaningfully but not explosively:
        100 GB  →  1.000× (no penalty, at threshold)
        1000 GB (1TB)   →  1.100× (+10%)
        10000 GB (10TB)  →  1.200× (+20%)
        100000 GB (100TB) →  1.300× (+30%)
    """
    if network_out_gb <= HIGH_EGRESS_THRESHOLD_GB:
        return 1.0
    ratio = network_out_gb / HIGH_EGRESS_THRESHOLD_GB
    return 1.0 + 0.10 * math.log10(ratio)


def compute_workload_density_multiplier(cpu: float, memory: float) -> float:
    """Scale cost when both CPU and Memory simultaneously exceed 60%.

    Mirrors multi-tenant resource overcommitment charges. The multiplier
    grows quadratically as utilisation rises toward 100%:
        CPU=60%, Mem=60%  →  1.000× (at threshold, no extra cost)
        CPU=80%, Mem=80%  →  1.056×
        CPU=100%, Mem=100% → 1.225×
    """
    if cpu <= WORKLOAD_CPU_THRESHOLD or memory <= WORKLOAD_MEM_THRESHOLD:
        return 1.0
    cpu_excess = (cpu - WORKLOAD_CPU_THRESHOLD) / (100.0 - WORKLOAD_CPU_THRESHOLD)
    mem_excess = (memory - WORKLOAD_MEM_THRESHOLD) / (100.0 - WORKLOAD_MEM_THRESHOLD)
    return 1.0 + 0.225 * cpu_excess * mem_excess


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def apply_business_adjustments(raw_model_cost: float, values: dict[str, Any]) -> dict[str, Any]:
    """Apply all post-model business rules and return a full cost breakdown.

    Args:
        raw_model_cost: The INR value returned directly by model.predict().
        values:         The sanitised + validated form values dict.

    Returns:
        A dict with every intermediate step for transparent display:
        {
            "baseline_cost":        float,  # Usage Qty × Cost/Qty × USD_TO_INR
            "ml_coefficient":       float,  # dimensionless scale (raw_model / baseline)
            "regional_multiplier":  float,
            "egress_multiplier":    float,
            "workload_multiplier":  float,
            "total_multiplier":     float,  # product of multipliers
            "final_cost_inr":       float,  # the number shown to the user
        }
    """
    USD_TO_INR_RATE = float(os.environ.get("USD_TO_INR_RATE", "84.0"))

    # 1. Deterministic linear baseline in proper currency
    try:
        usage_qty  = float(values.get("usage_quantity",   0) or 0)
        cost_per_q = float(values.get("cost_per_quantity", 0) or 0)
        baseline_usd = usage_qty * cost_per_q
        baseline_inr = baseline_usd * USD_TO_INR_RATE
    except (TypeError, ValueError):
        baseline_inr = 0.0

    # 2. Derive the ML Coefficient (Dimensionless)
    # This prevents adding raw currency to a baseline, treating the model instead
    # as a complexity multiplier over the baseline.
    MAX_ML_COEFFICIENT = 5.0  # Hard logical boundary to prevent extreme outliers

    if baseline_inr > 0:
        # Calculate raw coefficient and cap it using min() to prevent unbounded predictions
        raw_coefficient = raw_model_cost / baseline_inr
        ml_coefficient = min(raw_coefficient, MAX_ML_COEFFICIENT)
    else:
        # FREE TIER HANDLING
        # If the user's rate is $0, the baseline is 0. The ML model shouldn't invent a cost.
        ml_coefficient = 0.0
        baseline_inr = 0.0

    # 3. Individual multipliers
    region      = str(values.get("region", "") or "")
    network_out = float(values.get("network_out", 0) or 0) # Now in GB
    cpu         = float(values.get("cpu",     0) or 0)
    memory      = float(values.get("memory",  0) or 0)

    regional_mult = get_regional_multiplier(region)
    egress_mult   = compute_egress_penalty(network_out)
    workload_mult = compute_workload_density_multiplier(cpu, memory)

    total_multiplier = regional_mult * egress_mult * workload_mult

    # 4. Final calculation using consistent dimensions
    final_cost = baseline_inr * ml_coefficient * total_multiplier

    return {
        "baseline_cost":       round(baseline_inr, 4),
        "ml_coefficient":      round(ml_coefficient, 4),
        "regional_multiplier": round(regional_mult, 4),
        "egress_multiplier":   round(egress_mult, 4),
        "workload_multiplier": round(workload_mult, 4),
        "total_multiplier":    round(total_multiplier, 4),
        "final_cost_inr":      round(final_cost, 2),
    }
