"""
generate_dataset.py
===================
Reverse-engineered synthetic GCP billing dataset generator.

Schema recovered from:
  - src/data/preprocessing.py  → REQUIRED_COLUMNS, NUMERIC_COLUMNS, CATEGORICAL_COLUMNS
  - src/data/feature_engineering.py → feature derivation logic
  - models/feature_names.pkl       → exact categorical values from trained preprocessor
  - models/preprocessor.pkl        → OneHotEncoder categories (Service Name, Usage Unit, Region/Zone)
  - app/pricing.py                 → REGIONAL_MULTIPLIERS (region list), business logic ranges
  - app/services.py                → validation ranges (CPU 0-100, memory 0-100, qty >= 0)
  - tests/*.py                     → category values hard-coded in test payloads

Output: data/raw/gcp_final_approved_dataset.csv (≥ 5 000 rows)

Correlations preserved:
  - CPU/Memory co-vary (high-utilisation workloads run both high)
  - Network traffic scales with usage quantity
  - Cost per Quantity is service-specific (realistic GCP pricing tiers)
  - Total Cost (INR) = Usage Quantity × Cost per Quantity($) × 84 + noise
    (mirrors the deterministic baseline in app/pricing.py)
  - Usage Duration derived from Start/End dates
"""

from __future__ import annotations

import os
import sys
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Seed for reproducibility
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────────────────────────────────────
# Exact categorical values recovered from models/feature_names.pkl +
# models/preprocessor.pkl encoder.categories_
# ─────────────────────────────────────────────────────────────────────────────

SERVICE_NAMES = [
    "AI Platform",
    "BigQuery",
    "Cloud Armor",
    "Cloud Build",
    "Cloud CDN",
    "Cloud Data Fusion",
    "Cloud Dataproc",
    "Cloud Endpoints",
    "Cloud Functions",
    "Cloud Interconnect",
    "Cloud Load Balancing",
    "Cloud Memorystore",
    "Cloud NAT",
    "Cloud Run",
    "Cloud SQL",
    "Cloud Spanner",
    "Cloud Storage",
    "Cloud VPC",
    "Cloud VPN",
    "Compute Engine",
    "Container Registry",
    "Dataflow",
    "Firestore",
    "Kubernetes Engine",
    "Pub/Sub",
]

USAGE_UNITS = ["GB", "Hours", "Requests"]

# Exactly the 12 regions in the trained preprocessor
REGIONS = [
    "asia-east1",
    "asia-northeast1",
    "asia-southeast1",
    "australia-southeast1",
    "europe-north1",
    "europe-west1",
    "europe-west3",
    "northamerica-northeast1",
    "southamerica-east1",
    "us-central1",
    "us-east1",
    "us-west1",
]

# ─────────────────────────────────────────────────────────────────────────────
# Service-specific configuration
# Each entry: (typical_usage_unit, cost_per_unit_usd_range, qty_range)
# Ranges are (min, max) used with log-normal or uniform sampling.
# Assumptions are based on public GCP pricing sheets (approximate).
# ─────────────────────────────────────────────────────────────────────────────

SERVICE_CONFIG: dict[str, dict] = {
    "AI Platform": {
        "unit": "Hours",
        "cost_range": (0.08, 4.50),    # Training node-hours
        "qty_range": (1, 500),
        "cpu_mean": 75, "cpu_std": 15,
        "mem_mean": 70, "mem_std": 15,
        "net_in_scale": 5e8,
        "net_out_scale": 2e8,
    },
    "BigQuery": {
        "unit": "GB",
        "cost_range": (0.005, 0.05),   # per TB processed → normalised to GB
        "qty_range": (10, 100_000),
        "cpu_mean": 40, "cpu_std": 20,
        "mem_mean": 35, "mem_std": 20,
        "net_in_scale": 1e9,
        "net_out_scale": 5e8,
    },
    "Cloud Armor": {
        "unit": "Requests",
        "cost_range": (0.000001, 0.00002),
        "qty_range": (100_000, 50_000_000),
        "cpu_mean": 5, "cpu_std": 5,
        "mem_mean": 5, "mem_std": 5,
        "net_in_scale": 1e7,
        "net_out_scale": 5e6,
    },
    "Cloud Build": {
        "unit": "Hours",
        "cost_range": (0.003, 0.006),
        "qty_range": (1, 200),
        "cpu_mean": 60, "cpu_std": 20,
        "mem_mean": 55, "mem_std": 20,
        "net_in_scale": 2e8,
        "net_out_scale": 1e8,
    },
    "Cloud CDN": {
        "unit": "GB",
        "cost_range": (0.008, 0.02),
        "qty_range": (100, 500_000),
        "cpu_mean": 15, "cpu_std": 10,
        "mem_mean": 20, "mem_std": 10,
        "net_in_scale": 5e9,
        "net_out_scale": 1e10,
    },
    "Cloud Data Fusion": {
        "unit": "Hours",
        "cost_range": (0.35, 1.20),
        "qty_range": (1, 730),
        "cpu_mean": 50, "cpu_std": 20,
        "mem_mean": 60, "mem_std": 20,
        "net_in_scale": 3e8,
        "net_out_scale": 2e8,
    },
    "Cloud Dataproc": {
        "unit": "Hours",
        "cost_range": (0.01, 0.10),
        "qty_range": (10, 2000),
        "cpu_mean": 65, "cpu_std": 20,
        "mem_mean": 70, "mem_std": 15,
        "net_in_scale": 1e9,
        "net_out_scale": 5e8,
    },
    "Cloud Endpoints": {
        "unit": "Requests",
        "cost_range": (0.000003, 0.00003),
        "qty_range": (10_000, 10_000_000),
        "cpu_mean": 10, "cpu_std": 8,
        "mem_mean": 15, "mem_std": 8,
        "net_in_scale": 5e7,
        "net_out_scale": 3e7,
    },
    "Cloud Functions": {
        "unit": "Requests",
        "cost_range": (0.0000004, 0.0000025),
        "qty_range": (100_000, 100_000_000),
        "cpu_mean": 20, "cpu_std": 15,
        "mem_mean": 30, "mem_std": 15,
        "net_in_scale": 1e8,
        "net_out_scale": 5e7,
    },
    "Cloud Interconnect": {
        "unit": "Hours",
        "cost_range": (0.05, 0.50),
        "qty_range": (730, 8760),
        "cpu_mean": 10, "cpu_std": 8,
        "mem_mean": 10, "mem_std": 8,
        "net_in_scale": 1e10,
        "net_out_scale": 1e10,
    },
    "Cloud Load Balancing": {
        "unit": "Hours",
        "cost_range": (0.008, 0.025),
        "qty_range": (730, 8760),
        "cpu_mean": 20, "cpu_std": 10,
        "mem_mean": 25, "mem_std": 10,
        "net_in_scale": 5e9,
        "net_out_scale": 5e9,
    },
    "Cloud Memorystore": {
        "unit": "Hours",
        "cost_range": (0.016, 0.20),
        "qty_range": (730, 8760),
        "cpu_mean": 45, "cpu_std": 20,
        "mem_mean": 80, "mem_std": 10,
        "net_in_scale": 5e8,
        "net_out_scale": 2e8,
    },
    "Cloud NAT": {
        "unit": "Hours",
        "cost_range": (0.001, 0.01),
        "qty_range": (730, 8760),
        "cpu_mean": 5, "cpu_std": 5,
        "mem_mean": 5, "mem_std": 5,
        "net_in_scale": 1e9,
        "net_out_scale": 1e9,
    },
    "Cloud Run": {
        "unit": "Hours",
        "cost_range": (0.00002, 0.00024),
        "qty_range": (10, 10_000),
        "cpu_mean": 40, "cpu_std": 25,
        "mem_mean": 50, "mem_std": 25,
        "net_in_scale": 3e8,
        "net_out_scale": 2e8,
    },
    "Cloud SQL": {
        "unit": "Hours",
        "cost_range": (0.017, 3.50),
        "qty_range": (730, 8760),
        "cpu_mean": 55, "cpu_std": 20,
        "mem_mean": 65, "mem_std": 20,
        "net_in_scale": 3e9,
        "net_out_scale": 1e9,
    },
    "Cloud Spanner": {
        "unit": "Hours",
        "cost_range": (0.90, 3.00),
        "qty_range": (730, 8760),
        "cpu_mean": 60, "cpu_std": 20,
        "mem_mean": 70, "mem_std": 20,
        "net_in_scale": 2e9,
        "net_out_scale": 1e9,
    },
    "Cloud Storage": {
        "unit": "GB",
        "cost_range": (0.007, 0.023),
        "qty_range": (1, 1_000_000),
        "cpu_mean": 10, "cpu_std": 8,
        "mem_mean": 15, "mem_std": 8,
        "net_in_scale": 1e10,
        "net_out_scale": 5e9,
    },
    "Cloud VPC": {
        "unit": "Hours",
        "cost_range": (0.001, 0.01),
        "qty_range": (730, 8760),
        "cpu_mean": 5, "cpu_std": 5,
        "mem_mean": 10, "mem_std": 5,
        "net_in_scale": 5e9,
        "net_out_scale": 5e9,
    },
    "Cloud VPN": {
        "unit": "Hours",
        "cost_range": (0.05, 0.15),
        "qty_range": (730, 8760),
        "cpu_mean": 8, "cpu_std": 8,
        "mem_mean": 8, "mem_std": 8,
        "net_in_scale": 1e9,
        "net_out_scale": 1e9,
    },
    "Compute Engine": {
        "unit": "Hours",
        "cost_range": (0.01, 4.50),
        "qty_range": (730, 8760),
        "cpu_mean": 60, "cpu_std": 25,
        "mem_mean": 55, "mem_std": 25,
        "net_in_scale": 1e9,
        "net_out_scale": 5e8,
    },
    "Container Registry": {
        "unit": "GB",
        "cost_range": (0.026, 0.026),
        "qty_range": (1, 5000),
        "cpu_mean": 15, "cpu_std": 10,
        "mem_mean": 20, "mem_std": 10,
        "net_in_scale": 5e8,
        "net_out_scale": 3e8,
    },
    "Dataflow": {
        "unit": "Hours",
        "cost_range": (0.011, 0.056),
        "qty_range": (1, 5000),
        "cpu_mean": 70, "cpu_std": 15,
        "mem_mean": 75, "mem_std": 15,
        "net_in_scale": 2e9,
        "net_out_scale": 1e9,
    },
    "Firestore": {
        "unit": "Requests",
        "cost_range": (0.0000006, 0.0000018),
        "qty_range": (10_000, 500_000_000),
        "cpu_mean": 15, "cpu_std": 10,
        "mem_mean": 20, "mem_std": 10,
        "net_in_scale": 1e8,
        "net_out_scale": 5e7,
    },
    "Kubernetes Engine": {
        "unit": "Hours",
        "cost_range": (0.01, 0.10),
        "qty_range": (730, 8760),
        "cpu_mean": 65, "cpu_std": 20,
        "mem_mean": 60, "mem_std": 20,
        "net_in_scale": 2e9,
        "net_out_scale": 1e9,
    },
    "Pub/Sub": {
        "unit": "GB",
        "cost_range": (0.04, 0.07),
        "qty_range": (1, 100_000),
        "cpu_mean": 20, "cpu_std": 15,
        "mem_mean": 25, "mem_std": 15,
        "net_in_scale": 1e9,
        "net_out_scale": 5e8,
    },
}

# Regional price multipliers from app/pricing.py (used in cost calculation)
REGIONAL_MULTIPLIERS: dict[str, float] = {
    "us-central1": 1.000,
    "us-east1": 1.000,
    "us-west1": 1.010,
    "europe-west1": 1.060,
    "europe-west3": 1.080,
    "europe-north1": 1.070,
    "asia-east1": 1.100,
    "asia-northeast1": 1.120,
    "asia-southeast1": 1.100,
    "australia-southeast1": 1.140,
    "northamerica-northeast1": 1.040,
    "southamerica-east1": 1.180,
}

USD_TO_INR = 84.0


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def generate_resource_id(service: str, idx: int) -> str:
    prefix = service.lower().replace(" ", "-").replace("/", "-")[:12]
    return f"{prefix}-{idx:06d}"


def _log_uniform(lo: float, hi: float) -> float:
    """Sample uniformly in log space for wide-range quantities."""
    return math.exp(random.uniform(math.log(lo), math.log(hi)))


def generate_row(idx: int) -> dict:
    service = random.choice(SERVICE_NAMES)
    cfg = SERVICE_CONFIG[service]
    region = random.choice(REGIONS)

    # ── Dates ──────────────────────────────────────────────────────────────
    # Spread across 2 years of billing history (2023-01 to 2024-12)
    base_date = datetime(2023, 1, 1)
    start_offset_days = random.randint(0, 730)
    start_date = base_date + timedelta(days=start_offset_days)

    # Duration: 1 hour to 31 days, heavily weighted toward 1-30 days
    duration_days = random.choices(
        [1, 7, 14, 30, 31],
        weights=[0.10, 0.20, 0.20, 0.40, 0.10],
    )[0]
    end_date = start_date + timedelta(days=duration_days)

    # ── Usage Quantity ──────────────────────────────────────────────────────
    qty_lo, qty_hi = cfg["qty_range"]
    usage_quantity = _log_uniform(qty_lo, qty_hi)
    usage_quantity = round(usage_quantity, 4)

    # ── Cost per Quantity (USD) ─────────────────────────────────────────────
    cost_lo, cost_hi = cfg["cost_range"]
    cost_per_qty = round(random.uniform(cost_lo, cost_hi), 8)

    # ── CPU / Memory (correlated percentages) ───────────────────────────────
    cpu_mean = cfg["cpu_mean"]
    cpu_std = cfg["cpu_std"]
    mem_mean = cfg["mem_mean"]
    mem_std = cfg["mem_std"]

    # Introduce positive correlation via shared latent factor
    z = np.random.randn()  # shared workload pressure
    cpu = _clamp(cpu_mean + cpu_std * (0.7 * z + 0.3 * np.random.randn()), 0.1, 100.0)
    mem = _clamp(mem_mean + mem_std * (0.6 * z + 0.4 * np.random.randn()), 0.1, 100.0)
    cpu = round(cpu, 2)
    mem = round(mem, 2)

    # ── Network traffic (correlated with usage_quantity) ────────────────────
    net_in_scale = cfg["net_in_scale"]
    net_out_scale = cfg["net_out_scale"]
    qty_factor = math.log1p(usage_quantity) / 10.0  # soft scaling
    net_in = max(0.0, np.random.lognormal(math.log(max(net_in_scale * qty_factor, 1.0)), 1.2))
    net_out = max(0.0, np.random.lognormal(math.log(max(net_out_scale * qty_factor, 1.0)), 1.2))
    net_in = round(net_in, 0)
    net_out = round(net_out, 0)

    # ── Cost computation (deterministic baseline + regional adjustment) ──────
    regional_mult = REGIONAL_MULTIPLIERS.get(region, 1.05)
    base_usd = usage_quantity * cost_per_qty
    # Add realistic noise (±5 %)
    noise_factor = 1 + np.random.uniform(-0.05, 0.05)
    unrounded_cost_usd = base_usd * noise_factor * regional_mult
    rounded_cost_usd = round(unrounded_cost_usd, 6)
    total_cost_inr = round(unrounded_cost_usd * USD_TO_INR, 4)

    usage_unit = cfg["unit"]

    return {
        "Resource ID": generate_resource_id(service, idx),
        "Service Name": service,
        "Usage Quantity": usage_quantity,
        "Usage Unit": usage_unit,
        "Region/Zone": region,
        "CPU Utilization (%)": cpu,
        "Memory Utilization (%)": mem,
        "Network Inbound Data (Bytes)": net_in,
        "Network Outbound Data (Bytes)": net_out,
        "Usage Start Date": start_date.strftime("%Y-%m-%d"),
        "Usage End Date": end_date.strftime("%Y-%m-%d"),
        "Cost per Quantity ($)": cost_per_qty,
        "Unrounded Cost ($)": round(unrounded_cost_usd, 8),
        "Rounded Cost ($)": rounded_cost_usd,
        "Total Cost (INR)": total_cost_inr,
    }


def generate_dataset(n_rows: int = 6000) -> pd.DataFrame:
    print(f"Generating {n_rows} rows ...")
    rows = [generate_row(i) for i in range(n_rows)]
    df = pd.DataFrame(rows)

    # Guarantee every service / unit / region appears at least once
    guaranteed: list[dict] = []
    for svc in SERVICE_NAMES:
        row = generate_row(n_rows + len(guaranteed))
        row["Service Name"] = svc
        cfg = SERVICE_CONFIG[svc]
        row["Usage Unit"] = cfg["unit"]
        guaranteed.append(row)

    for unit in USAGE_UNITS:
        row = generate_row(n_rows + len(guaranteed))
        row["Usage Unit"] = unit
        guaranteed.append(row)

    for region in REGIONS:
        row = generate_row(n_rows + len(guaranteed))
        row["Region/Zone"] = region
        guaranteed.append(row)

    df_guaranteed = pd.DataFrame(guaranteed)
    df = pd.concat([df, df_guaranteed], ignore_index=True)
    df.index.name = None

    print(f"Total rows generated: {len(df)}")
    print(f"Service Name unique values ({df['Service Name'].nunique()}): {sorted(df['Service Name'].unique())}")
    print(f"Usage Unit unique values ({df['Usage Unit'].nunique()}): {sorted(df['Usage Unit'].unique())}")
    print(f"Region/Zone unique values ({df['Region/Zone'].nunique()}): {sorted(df['Region/Zone'].unique())}")
    print(f"Cost (INR) range: [{df['Total Cost (INR)'].min():.2f}, {df['Total Cost (INR)'].max():.2f}]")
    return df


def validate_dataset(df: pd.DataFrame) -> None:
    """Run all preprocessing and feature engineering checks on the dataset."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.data.preprocessing import preprocess_dataset, REQUIRED_COLUMNS
    from src.data.feature_engineering import create_features

    print("\nValidating dataset through preprocessing pipeline ...")
    # Column check
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"

    processed = preprocess_dataset(df.copy())
    print(f"  preprocess_dataset -> OK  shape={processed.shape}")

    sample = processed.iloc[:5].copy()
    engineered = create_features(sample)
    assert "Usage Duration (Hours)" in engineered.columns
    assert "Total Network Traffic" in engineered.columns
    print(f"  create_features     -> OK  columns={list(engineered.columns)}")
    print("Validation PASSED (OK)")


def main() -> None:
    output_path = Path(__file__).resolve().parents[1] / "data" / "raw" / "gcp_final_approved_dataset.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_dataset(n_rows=6000)
    validate_dataset(df)

    df.to_csv(output_path, index=False)
    print(f"\nDataset saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
