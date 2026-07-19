"""
app/ai_assistant.py
===================
StadiumIQ — Gemini AI-powered Stadium Operations Director

Provides real-time, actionable intelligence for FIFA World Cup 2026
stadium operations including crowd management, security, emergency
response, staffing, logistics, and fan experience optimization.

Gracefully degrades to template-based responses when GEMINI_API_KEY
is not configured, ensuring the application always returns useful guidance.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Display-name aliases (internal model values → stadium terminology)
# ---------------------------------------------------------------------------

ZONE_ALIASES: dict[str, str] = {
    "AI Platform":           "AI Ops Center",
    "BigQuery":              "Fan Analytics Platform",
    "Cloud Armor":           "Cybersecurity Shield",
    "Cloud Build":           "Match Day Setup",
    "Cloud CDN":             "Fan WiFi & Streaming",
    "Cloud Data Fusion":     "Multi-Source Data Integration",
    "Cloud Dataproc":        "Real-Time Match Analytics",
    "Cloud Endpoints":       "Stadium API Gateway",
    "Cloud Functions":       "Emergency Response Unit",
    "Cloud Interconnect":    "Inter-Venue Link",
    "Cloud Load Balancing":  "Security Checkpoint",
    "Cloud Memorystore":     "VIP Hospitality Suite",
    "Cloud NAT":             "Transportation Hub",
    "Cloud Run":             "Crowd Management System",
    "Cloud SQL":             "Ticketing & Access Control",
    "Cloud Spanner":         "Real-Time Scoreboard",
    "Cloud Storage":         "Broadcast & Media Archive",
    "Cloud VPC":             "Stadium Network Infrastructure",
    "Cloud VPN":             "Communications Center",
    "Compute Engine":        "Field Operations Hub",
    "Container Registry":    "App Distribution Platform",
    "Dataflow":              "Live Stream Processing",
    "Firestore":             "Fan Profile Database",
    "Kubernetes Engine":     "Stadium Control Network",
    "Pub/Sub":               "Event Notification System",
}

VENUE_ALIASES: dict[str, str] = {
    "us-central1":              "MetLife Stadium (NJ/NY)",
    "us-east1":                 "AT&T Stadium (Dallas)",
    "us-east4":                 "Lincoln Financial (Philadelphia)",
    "us-east5":                 "Gillette Stadium (Boston)",
    "us-west1":                 "SoFi Stadium (Los Angeles)",
    "us-west2":                 "Rose Bowl (Pasadena)",
    "us-west3":                 "Levi's Stadium (San Jose)",
    "us-west4":                 "Allegiant Stadium (Las Vegas)",
    "us-south1":                "NRG Stadium (Houston)",
    "northamerica-northeast1":  "BC Place (Vancouver)",
    "northamerica-northeast2":  "BMO Field (Toronto)",
    "europe-west1":             "Arrowhead Stadium (Kansas City)",
    "europe-west2":             "Mercedes-Benz Stadium (Atlanta)",
    "europe-west3":             "Hard Rock Stadium (Miami)",
    "europe-west4":             "Estadio Azteca (Mexico City)",
    "europe-west6":             "Estadio AKRON (Guadalajara)",
    "europe-west8":             "Estadio de Monterrey",
    "europe-west9":             "Estadio Ciudad de Guadalajara",
    "europe-west10":            "Estadio Universitario (NL)",
    "europe-west12":            "Estadio Cuauhtemoc (Puebla)",
    "europe-central2":          "Estadio Olimpico (Mexico)",
    "europe-north1":            "Estadio La Corregidora",
    "europe-southwest1":        "Estadio Tecnologico (NL)",
    "asia-east1":               "Kansas City Arrowhead",
    "asia-east2":               "Dallas AT&T Operations",
    "asia-northeast1":          "Seattle Lumen Field Ops",
    "asia-northeast2":          "Portland Providence Park",
    "asia-northeast3":          "San Diego Snapdragon",
    "asia-south1":              "Denver Empower Field",
    "asia-south2":              "Cincinnati Paycor Stadium",
    "asia-southeast1":          "Nashville Nissan Stadium",
    "asia-southeast2":          "Pittsburgh Acrisure",
    "australia-southeast1":     "Hard Rock Stadium (Miami)",
    "australia-southeast2":     "Camping World Stadium (Orlando)",
    "southamerica-east1":       "NRG Stadium (Houston)",
    "southamerica-west1":       "Estadio La Bombonera (Alt)",
    "me-west1":                 "Allegiant Stadium (Las Vegas)",
    "me-central1":              "State Farm Stadium (Glendale)",
    "me-central2":              "Raymond James (Tampa)",
    "africa-south1":            "MetLife International Zone",
}

# ---------------------------------------------------------------------------
# Scenario-specific fallback recommendations (used when Gemini API unavailable)
# ---------------------------------------------------------------------------

_FALLBACK_RECOMMENDATIONS: dict[str, list[str]] = {
    "high_load": [
        "Activate overflow crowd management protocols — deploy additional stewards to gates C, D, and F.",
        "Trigger dynamic wayfinding signage updates to redistribute fan flow from congested concourses.",
        "Alert catering and merchandise managers to increase staffing levels by 30% in high-traffic zones.",
    ],
    "emergency": [
        "Initiate emergency broadcast over PA system — direct fans to designated assembly points.",
        "Deploy medical response teams to sectors reporting elevated density above 85%.",
        "Coordinate with local law enforcement for perimeter control and evacuation route clearance.",
    ],
    "high_egress": [
        "Pre-position transport coordination teams at all exit gates 45 minutes before final whistle.",
        "Activate staggered exit strategy: VIP exits first, followed by sector-by-sector release.",
        "Signal public transport operators to increase shuttle frequency by 2x during post-match egress.",
    ],
    "vip": [
        "Confirm VIP hospitality suite staffing ratios meet FIFA protocol (1 staff per 8 guests).",
        "Verify premium food & beverage inventory levels — replenishment threshold at 30% capacity.",
        "Coordinate VIP shuttle logistics with venue security for seamless match-day experience.",
    ],
    "default": [
        "Monitor real-time crowd density feeds across all stadium zones — adjust staffing if thresholds exceeded.",
        "Confirm all emergency exits are unobstructed and access control scanners are operational.",
        "Brief incident command teams on match-day protocols and communication channels.",
    ],
    "low_load": [
        "Optimize staffing efficiency — consider reducing active service points during low-attendance periods.",
        "Use this window to conduct preventive maintenance checks on critical stadium infrastructure.",
        "Pre-position operational resources for anticipated peak arrival 90 minutes before kick-off.",
    ],
}


def _get_fallback_recommendations(values: dict[str, Any]) -> list[str]:
    """Return scenario-appropriate fallback recommendations without the Gemini API."""
    cpu = float(values.get("cpu", 50) or 50)
    memory = float(values.get("memory", 50) or 50)
    network_out = float(values.get("network_out", 0) or 0)
    zone = str(values.get("service_name", ""))

    if memory >= 80 or cpu >= 80:
        return _FALLBACK_RECOMMENDATIONS["high_load"]
    if network_out > 200:
        return _FALLBACK_RECOMMENDATIONS["high_egress"]
    if zone in ("Cloud Memorystore", "AI Platform"):
        return _FALLBACK_RECOMMENDATIONS["vip"]
    if memory < 30 and cpu < 30:
        return _FALLBACK_RECOMMENDATIONS["low_load"]
    return _FALLBACK_RECOMMENDATIONS["default"]


def _build_gemini_prompt(values: dict[str, Any], predicted_cost: float) -> str:
    """Construct the Gemini prompt with full stadium operational context."""
    zone_raw = str(values.get("service_name", "General Operations"))
    venue_raw = str(values.get("region", "us-central1"))
    zone_display = ZONE_ALIASES.get(zone_raw, zone_raw)
    venue_display = VENUE_ALIASES.get(venue_raw, venue_raw)

    cpu = float(values.get("cpu", 50) or 50)
    memory = float(values.get("memory", 50) or 50)
    network_in = float(values.get("network_in", 0) or 0)
    network_out = float(values.get("network_out", 0) or 0)
    qty = float(values.get("usage_quantity", 0) or 0)
    unit = str(values.get("usage_unit", "Hours"))
    start = str(values.get("usage_start", ""))
    end = str(values.get("usage_end", ""))

    # Map technical metrics to stadium language
    crowd_density = f"{memory:.0f}%"
    system_load = f"{cpu:.0f}%"
    arrival_flow = f"{network_in:.1f} GB/hr"
    exit_flow = f"{network_out:.1f} GB/hr"
    resource_volume = f"{qty:,.0f} {unit}"

    return f"""You are StadiumIQ, an elite AI Stadium Operations Director for FIFA World Cup 2026.

CURRENT OPERATIONAL BRIEF:
- Stadium Zone: {zone_display}
- Venue: {venue_display}
- Crowd Capacity Load: {crowd_density}
- System Activity Level: {system_load}
- Fan Arrival Flow: {arrival_flow}
- Fan Exit/Egress Flow: {exit_flow}
- Resource Volume: {resource_volume}
- Operational Window: {start} to {end}
- Estimated Operational Cost: ₹{predicted_cost:,.2f}

Based on this operational data, provide exactly 3 specific, actionable recommendations for the stadium operations team. Each recommendation must:
1. Address a real operational concern suggested by the metrics above
2. Be specific and immediately actionable (not generic advice)
3. Reference the zone or venue when relevant
4. Be 1-2 sentences maximum

Format your response as a valid JSON array with exactly 3 string elements, like:
["recommendation 1", "recommendation 2", "recommendation 3"]

Focus on: crowd safety, staff deployment, logistics, emergency preparedness, or fan experience — whichever is most relevant to the current metrics."""


def get_ai_recommendations(values: dict[str, Any], predicted_cost: float) -> dict[str, Any]:
    """
    Generate AI-powered stadium operations recommendations.

    Uses Google Gemini when GEMINI_API_KEY is configured; gracefully
    falls back to scenario-based template recommendations otherwise.

    Args:
        values:         The sanitised form values dict from services.py.
        predicted_cost: The final predicted cost (INR) from the pricing engine.

    Returns:
        dict with keys:
            "recommendations": list[str]   — 3 actionable items
            "source":          str         — "gemini" | "fallback"
            "zone_display":    str         — human-readable zone name
            "venue_display":   str         — human-readable venue name
    """
    zone_raw = str(values.get("service_name", ""))
    venue_raw = str(values.get("region", ""))
    zone_display = ZONE_ALIASES.get(zone_raw, zone_raw)
    venue_display = VENUE_ALIASES.get(venue_raw, venue_raw)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        logger.info("GEMINI_API_KEY not set — using fallback recommendations.")
        return {
            "recommendations": _get_fallback_recommendations(values),
            "source": "fallback",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }

    try:
        # Try new google-genai SDK first, fall back to deprecated google.generativeai
        try:
            from google import genai as genai_new  # type: ignore[import]
            client = genai_new.Client(api_key=api_key)
            prompt = _build_gemini_prompt(values, predicted_cost)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
            )
            raw_text = response.text.strip()
        except (ImportError, AttributeError):
            import google.generativeai as genai_old  # type: ignore[import]
            genai_old.configure(api_key=api_key)
            model = genai_old.GenerativeModel("gemini-1.5-flash")
            prompt = _build_gemini_prompt(values, predicted_cost)
            response = model.generate_content(
                prompt,
                generation_config=genai_old.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=512,
                ),
            )
            raw_text = response.text.strip()

        # Parse JSON array from response
        # Gemini sometimes wraps in markdown code blocks
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        recommendations = json.loads(raw_text)
        if not isinstance(recommendations, list):
            raise ValueError("Expected JSON array")

        # Ensure exactly 3 items
        recommendations = [str(r) for r in recommendations[:3]]
        while len(recommendations) < 3:
            recommendations.extend(_get_fallback_recommendations(values)[:3 - len(recommendations)])

        logger.info("Gemini AI recommendations generated successfully.")
        return {
            "recommendations": recommendations,
            "source": "gemini",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }

    except Exception as exc:
        logger.warning("Gemini AI call failed (%s) — using fallback.", exc)
        return {
            "recommendations": _get_fallback_recommendations(values),
            "source": "fallback",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }


def get_stadium_status() -> dict[str, Any]:
    """
    Return simulated live stadium status metrics for the dashboard.

    In a production deployment this would pull from real IoT sensors,
    access-control systems, and crowd-flow APIs. For the WC2026 demo
    this returns dynamically generated values that change each call.
    """
    import random
    import time

    ts = int(time.time())
    rng = random.Random(ts // 30)  # stable per 30-second window

    venues = [
        "MetLife Stadium (NJ/NY)",
        "AT&T Stadium (Dallas)",
        "SoFi Stadium (Los Angeles)",
        "Hard Rock Stadium (Miami)",
        "BC Place (Vancouver)",
        "Mercedes-Benz Stadium (Atlanta)",
        "Arrowhead Stadium (Kansas City)",
        "NRG Stadium (Houston)",
    ]

    statuses = []
    for venue in rng.sample(venues, 4):
        capacity = rng.randint(45, 98)
        alert = "NOMINAL"
        alert_class = "ok"
        if capacity >= 90:
            alert = "HIGH DENSITY"
            alert_class = "warn"
        if capacity >= 95:
            alert = "CRITICAL"
            alert_class = "danger"

        statuses.append({
            "venue": venue,
            "capacity_pct": capacity,
            "alert": alert,
            "alert_class": alert_class,
            "active_staff": rng.randint(200, 800),
            "active_gates": rng.randint(8, 24),
        })

    return {
        "venues": statuses,
        "global_alert": "ALL SYSTEMS NOMINAL" if all(s["alert"] == "NOMINAL" for s in statuses) else "ELEVATED MONITORING",
        "active_matches": rng.randint(0, 4),
        "total_fans_today": rng.randint(50_000, 320_000),
    }
