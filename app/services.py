"""
app/services.py
===============
Service layer implementation for StadiumIQ form sanitization, history logs, and predictions.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import pandas as pd
from flask import Response

from src.model.predict import predict_cost
from app.database import get_db_connection
from app.pricing import apply_business_adjustments

MAX_DURATION_HOURS: int = 24 * 365 * 20

# Numeric fields where users may accidentally include unit suffixes
_SANITIZED_NUMERIC_FIELDS: frozenset[str] = frozenset([
    "usage_quantity", "cpu", "memory", "network_in", "network_out", "cost_per_quantity"
])

# Numeric validation bounds: field_name -> (label, min_val, max_val)
_NUMERIC_CONSTRAINTS: dict[str, tuple[str, float | None, float | None]] = {
    "usage_quantity": ("Usage Quantity", 0.0, None),
    "cpu": ("CPU Utilization", 0.0, 100.0),
    "memory": ("Memory Utilization", 0.0, 100.0),
    "network_in": ("Network Inbound Data", 0.0, None),
    "network_out": ("Network Outbound Data", 0.0, None),
    "cost_per_quantity": ("Cost per Quantity", 0.0, None),
}


def _strip_non_numeric(raw: str) -> str:
    """Strip non-numeric characters from a string, keeping digits, dot, and minus.

    Examples:
        '64%'         -> '64'
        '1.5 GB'      -> '1.5'
        '1024 bytes'  -> '1024'
        '  50 '       -> '50'
        '-1'          -> '-1'   (preserves negatives for validation to catch)
    """
    cleaned = re.sub(r"[^\d.\-]", "", raw.strip())
    return cleaned if cleaned else raw.strip()


def sanitize_form_data(form_data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Sanitizes, strips, validates form inputs, and collects logical and structural errors.

    Args:
        form_data: Dictionary of raw HTTP form values.

    Returns:
        A tuple of (errors_list, values_dict).
    """
    from app.blueprints.main import _get_form_options
    options = _get_form_options()

    errors: list[str] = []
    
    # Extract string values cleanly
    values: dict[str, Any] = {
        key: (form_data.get(key) or "").strip()
        for key in [
            "service_name", "usage_quantity", "usage_unit", "region", "cpu",
            "memory", "network_in", "network_out", "usage_start", "usage_end",
            "cost_per_quantity"
        ]
    }

    # Validate Categorical Dropdowns
    if not values["service_name"]:
        errors.append("Service Name is required.")
    elif values["service_name"] not in options["service_names"]:
        errors.append(f"Unknown Service Name: {values['service_name']}")

    if not values["usage_unit"]:
        errors.append("Usage Unit is required.")
    elif values["usage_unit"] not in options["usage_units"]:
        errors.append(f"Unknown Usage Unit: {values['usage_unit']}")

    if not values["region"]:
        errors.append("Region is required.")
    elif values["region"] not in options["regions"]:
        errors.append(f"Unknown Region: {values['region']}")

    # Validate and clean numeric inputs
    for field_name, (label, min_val, max_val) in _NUMERIC_CONSTRAINTS.items():
        raw_value = values[field_name]
        if not raw_value:
            errors.append(f"{label} is required.")
            continue

        if field_name in _SANITIZED_NUMERIC_FIELDS:
            raw_value = _strip_non_numeric(raw_value)
            values[field_name] = raw_value

        try:
            val = float(raw_value)
            values[field_name] = val
            
            # Enforce range limits
            if min_val is not None and val < min_val:
                errors.append(f"{label} must be greater than or equal to {min_val}.")
            if max_val is not None and val > max_val:
                errors.append(f"{label} must be between {min_val} and {max_val}.")
        except (TypeError, ValueError):
            errors.append(f"{label} must be a valid number (got: {raw_value!r}).")

    # Validate dates
    if not values["usage_start"]:
        errors.append("Usage Start Date is required.")
    if not values["usage_end"]:
        errors.append("Usage End Date is required.")

    if values.get("usage_start") and values.get("usage_end"):
        try:
            start_date = pd.to_datetime(values["usage_start"])
            end_date = pd.to_datetime(values["usage_end"])
            if start_date > end_date:
                errors.append("Usage Start Date cannot be later than Usage End Date.")
            duration_hours = (end_date - start_date).total_seconds() / 3600
            if duration_hours > MAX_DURATION_HOURS:
                errors.append("Usage duration is too large. Please choose a shorter range.")
            values["usage_start"] = start_date.strftime("%Y-%m-%d")
            values["usage_end"] = end_date.strftime("%Y-%m-%d")
        except Exception as exc:
            errors.append(f"Usage dates must be valid dates. {exc}")

    return errors, values


def build_input_dataframe(values: dict[str, Any]) -> pd.DataFrame:
    """Builds a single-row pandas DataFrame matching preprocessing.REQUIRED_COLUMNS contract.

    Args:
        values: Dictionary of sanitized cost assessment inputs.

    Returns:
        Structured pandas DataFrame.
    """
    ts = datetime.now(timezone.utc).timestamp()
    return pd.DataFrame(
        [
            {
                "Resource ID": f"temp-{ts}",
                "Service Name": values["service_name"],
                "Usage Quantity": values["usage_quantity"],
                "Usage Unit": values["usage_unit"],
                "Region/Zone": values["region"],
                "CPU Utilization (%)": values["cpu"],
                "Memory Utilization (%)": values["memory"],
                "Network Inbound Data (Bytes)": float(values["network_in"]) * 1e9 if values["network_in"] else 0.0,
                "Network Outbound Data (Bytes)": float(values["network_out"]) * 1e9 if values["network_out"] else 0.0,
                "Usage Start Date": pd.to_datetime(values["usage_start"]),
                "Usage End Date": pd.to_datetime(values["usage_end"]),
                "Cost per Quantity ($)": values["cost_per_quantity"],
                "Unrounded Cost ($)": 0.0,
                "Rounded Cost ($)": 0.0,
                "Total Cost (INR)": 0.0,
            }
        ]
    )


def save_prediction(values: dict[str, Any], predicted_cost: float) -> None:
    """Persists prediction inputs and raw outputs to database.

    Args:
        values: Predictor inputs.
        predicted_cost: Evaluated operational cost.
    """
    connection = get_db_connection()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    connection.execute(
        """
        INSERT INTO prediction_history (
            timestamp, service_name, usage_quantity, usage_unit, region, cpu,
            memory, network_in, network_out, usage_start, usage_end,
            cost_per_quantity, predicted_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_str,
            values["service_name"],
            values["usage_quantity"],
            values["usage_unit"],
            values["region"],
            values["cpu"],
            values["memory"],
            values["network_in"],
            values["network_out"],
            values["usage_start"],
            values["usage_end"],
            values["cost_per_quantity"],
            predicted_cost,
        ),
    )
    connection.commit()
    connection.close()


def get_prediction_history(limit: int | None = None, search: str | None = None) -> list[dict[str, Any]]:
    """Retrieves historic operations assessments filtered by search constraints.

    Args:
        limit: Max results count.
        search: Substring queries for service_name or region.

    Returns:
        List of database records converted to dictionaries.
    """
    connection = get_db_connection()
    query = "SELECT * FROM prediction_history"
    params: list[Any] = []
    if search:
        query += " WHERE lower(service_name) LIKE ? OR lower(region) LIKE ?"
        search_term = f"%{search.lower()}%"
        params.extend([search_term, search_term])
    query += " ORDER BY id DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    rows = connection.execute(query, params).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_dashboard_stats(search: str | None = None) -> dict[str, Any]:
    """Generates operational statistics and chart data aggregates.

    Args:
        search: Optional search text to filter inputs.

    Returns:
        Aggregated statistics structure.
    """
    rows = get_prediction_history(search=search)
    if not rows:
        return {
            "total_predictions": 0,
            "latest_prediction": None,
            "predictions_per_day": {"labels": [], "values": []},
            "average_predicted_cost": 0.0,
            "top_services": {"labels": [], "values": []},
            "top_regions": {"labels": [], "values": []},
        }

    latest_prediction = rows[0]
    daily_counts: dict[str, int] = {}
    service_counts: dict[str, int] = {}
    region_counts: dict[str, int] = {}
    total_cost = 0.0

    for row in rows:
        day = row["timestamp"][:10]
        daily_counts[day] = daily_counts.get(day, 0) + 1
        service_counts[row["service_name"]] = service_counts.get(row["service_name"], 0) + 1
        region_counts[row["region"]] = region_counts.get(row["region"], 0) + 1
        total_cost += row["predicted_cost"]

    return {
        "total_predictions": len(rows),
        "latest_prediction": dict(latest_prediction),
        "predictions_per_day": {
            "labels": list(daily_counts.keys()),
            "values": list(daily_counts.values()),
        },
        "average_predicted_cost": round(total_cost / len(rows), 2),
        "top_services": {
            "labels": list(service_counts.keys()),
            "values": list(service_counts.values()),
        },
        "top_regions": {
            "labels": list(region_counts.keys()),
            "values": list(region_counts.values()),
        },
    }


def delete_prediction(prediction_id: int) -> None:
    """Removes a single operational assessment record.

    Args:
        prediction_id: Database ID of the record.
    """
    connection = get_db_connection()
    connection.execute("DELETE FROM prediction_history WHERE id = ?", (prediction_id,))
    connection.commit()
    connection.close()


def generate_csv(rows: list[dict[str, Any]]) -> str:
    """Generates structured CSV export representation of assessment rows.

    Args:
        rows: Prediction history rows.

    Returns:
        Exportable CSV raw string content.
    """
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "timestamp",
            "service_name",
            "usage_quantity",
            "usage_unit",
            "region",
            "cpu",
            "memory",
            "network_in",
            "network_out",
            "usage_start",
            "usage_end",
            "cost_per_quantity",
            "predicted_cost",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return output.getvalue()


def perform_prediction(values: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Invokes predictor, calibrates rates, and logs output data.

    Args:
        values: Sanitized cost inputs.

    Returns:
        A tuple of (final_cost_inr, cost_breakdown).
    """
    dataframe = build_input_dataframe(values)
    prediction = predict_cost(dataframe)
    raw_cost = float(prediction[0])

    breakdown = apply_business_adjustments(raw_cost, values)
    final_cost = breakdown["final_cost_inr"]

    save_prediction(values, final_cost)
    return final_cost, breakdown
