"""
app/ai_assistant.py
===================
StadiumIQ — Gemini AI-powered Stadium Operations Director

Provides real-time, actionable operational intelligence for FIFA World Cup 2026
across 13 distinct operational domains. Each domain has a purpose-built
system prompt tuned to the specific decision context operations staff face.

Domains:
  1.  Crowd Congestion Monitoring
  2.  AI Operational Recommendations
  3.  Security Deployment
  4.  Medical Incident Response
  5.  Volunteer & Staff Allocation
  6.  Fan Assistance
  7.  Gate Optimization
  8.  Parking Management
  9.  Food & Inventory Monitoring
  10. Weather Impact Analysis
  11. Match-Day Readiness
  12. Emergency Evacuation Support
  13. Venue Maintenance Planning
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Display-name aliases (internal model values -> stadium terminology)
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
    "us-east4":                 "Lincoln Financial Field (Philadelphia)",
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
    "europe-north1":            "Estadio de Monterrey",
    "australia-southeast1":     "Camping World Stadium (Orlando)",
    "southamerica-east1":       "NRG Stadium (Houston)",
    "me-central2":              "Raymond James Stadium (Tampa)",
    "me-west1":                 "State Farm Stadium (Glendale)",
}

# ---------------------------------------------------------------------------
# 13 Operational Domain Definitions
# ---------------------------------------------------------------------------

OPERATIONAL_DOMAINS: list[dict[str, Any]] = [
    {
        "id": "crowd_congestion",
        "title": "Crowd Congestion Monitoring",
        "icon": "crowd",
        "color": "orange",
        "description": "Monitor and manage spectator density across gates, concourses, and seating sections to prevent dangerous overcrowding.",
        "placeholder": "Describe the congestion situation: location (e.g. Gate 7 North concourse), estimated crowd count, severity (mild/moderate/severe), time to kickoff, available stewards on site.",
        "example": "Gate C concourse showing high density — approximately 3,000 fans queued. Match kicks off in 35 minutes. We have 12 stewards on site. Turnstile scan rate has dropped to 180/min from normal 420/min.",
        "zone_hint": "Cloud Run",
    },
    {
        "id": "ai_recommendations",
        "title": "AI Operational Recommendations",
        "icon": "ai",
        "color": "green",
        "description": "Get real-time AI-driven guidance on staffing, logistics, and resource deployment for any operational situation.",
        "placeholder": "Describe your current operational situation and what decision or recommendation you need from the AI Director.",
        "example": "We are 90 minutes from kickoff at MetLife. Attendance is tracking 15,000 above forecast. What should we prioritise in the next 30 minutes?",
        "zone_hint": "AI Platform",
    },
    {
        "id": "security_deployment",
        "title": "Security Deployment",
        "icon": "security",
        "color": "red",
        "description": "Optimise security personnel placement, access control, and threat response across all venue entry points and perimeters.",
        "placeholder": "Describe the security situation: threat level, specific location, incident type (suspicious item, crowd disorder, VIP threat), current security assets available.",
        "example": "Suspicious bag reported at Gate 12 by a steward. Crowd in that zone is approximately 800 people. We have 4 security officers within 200m. Local police ETA 8 minutes.",
        "zone_hint": "Cloud Load Balancing",
    },
    {
        "id": "medical_response",
        "title": "Medical Incident Response",
        "icon": "medical",
        "color": "red",
        "description": "Coordinate rapid medical response for fan injuries, cardiac events, heat exhaustion, and mass casualty preparedness.",
        "placeholder": "Describe the medical incident: type (cardiac, trauma, heat exhaustion, crowd crush injury), location, patient count, current medical resources on site, nearest medical post.",
        "example": "Fan collapse in Section 114, Row 28. Possible cardiac event. Stadium medic en route, 3 minutes away. AED is 45m from location in Concourse B. Fan is unresponsive, bystander performing CPR.",
        "zone_hint": "Cloud Functions",
    },
    {
        "id": "staff_allocation",
        "title": "Volunteer & Staff Allocation",
        "icon": "staff",
        "color": "blue",
        "description": "Dynamically allocate stewards, volunteers, medical staff, and operations personnel based on real-time demand across venue zones.",
        "placeholder": "Describe the staffing gap: zone with shortage, current staffing level, required level, available reserve staff locations, time sensitivity.",
        "example": "South Stand running short — we have 8 stewards covering 12,000 fans. Recommended ratio is 1:150. Need to reallocate 20 additional stewards. Reserve pool of 35 currently at briefing room B2.",
        "zone_hint": "Compute Engine",
    },
    {
        "id": "fan_assistance",
        "title": "Fan Assistance",
        "icon": "fan",
        "color": "purple",
        "description": "Handle accessibility requests, lost-and-found, language assistance, first-time attendee guidance, and fan welfare situations.",
        "placeholder": "Describe the fan assistance situation: issue type (accessibility, lost child, language barrier, medical non-emergency, ticket dispute), fan location, urgency level.",
        "example": "Family of 5 at Gate A info booth. Parents are deaf, have a child with wheelchair needs. Tickets show upper tier seating — no accessible route available. Match starts in 20 minutes.",
        "zone_hint": "Cloud Memorystore",
    },
    {
        "id": "gate_optimization",
        "title": "Gate Optimization",
        "icon": "gate",
        "color": "teal",
        "description": "Optimise gate throughput, manage bottlenecks, redirect fan flows, and balance arrival distribution across all venue entry points.",
        "placeholder": "Describe the gate situation: which gates are overloaded, current scan rates vs target, estimated fan backlog, available alternative gates, time pressure.",
        "example": "Gates 1–4 (North) processing 1,200 fans/min against a 2,400/min capacity target. Gates 9–12 (South) at 40% utilisation. 18,000 fans still to enter. Kickoff in 45 minutes.",
        "zone_hint": "Cloud SQL",
    },
    {
        "id": "parking_management",
        "title": "Parking Management",
        "icon": "parking",
        "color": "yellow",
        "description": "Manage parking lot capacity, traffic flow, shuttle coordination, VIP parking, and post-match egress logistics.",
        "placeholder": "Describe the parking situation: lots at capacity, traffic backup severity, shuttle bus status, estimated departure wave timing, VIP access conflicts.",
        "example": "Lots A, B, C at 100% capacity. Lot D at 78%. Traffic on Route 3 backed up 2.1 miles from main entrance. Shuttle buses running 12 min late due to Route 1 closure. Post-match wave starts in 2 hours.",
        "zone_hint": "Cloud NAT",
    },
    {
        "id": "food_inventory",
        "title": "Food & Inventory Monitoring",
        "icon": "food",
        "color": "amber",
        "description": "Monitor concession inventory levels, manage stock replenishment, handle high-demand alerts, and coordinate catering logistics.",
        "placeholder": "Describe the inventory situation: concession zone, items running low, current stock level vs projected demand, resupply lead time, alternatives available.",
        "example": "Concourse B beer stock at 15% of opening inventory with 75 minutes of match time remaining. Projected demand suggests stock-out in 40 minutes. Backup warehouse is 8 minutes by cart. Hot dog buns also at 20%.",
        "zone_hint": "Cloud Memorystore",
    },
    {
        "id": "weather_impact",
        "title": "Weather Impact Analysis",
        "icon": "weather",
        "color": "sky",
        "description": "Assess weather conditions, issue operational guidance for extreme heat, lightning, heavy rain, wind, and implement contingency protocols.",
        "placeholder": "Describe the weather situation: current conditions, forecast change, wet bulb temperature (for heat), lightning distance, wind speed, how it affects operations.",
        "example": "Current temperature 97°F (36°C), humidity 78%, wet bulb 31°C. Lightning detected 8 miles NW, tracking toward stadium. Match is 60 minutes in. 55,000 fans in open seating. Expected arrival in 25 minutes.",
        "zone_hint": "BigQuery",
    },
    {
        "id": "match_readiness",
        "title": "Match-Day Readiness",
        "icon": "readiness",
        "color": "green",
        "description": "Generate a comprehensive pre-match readiness assessment covering all operational domains, identify gaps, and issue a final go/no-go recommendation.",
        "placeholder": "Provide your pre-match status: T-minus time, venue name, expected attendance, known issues or risks across security, medical, crowd, catering, and transport.",
        "example": "T-minus 3 hours at MetLife Stadium. Expected attendance 82,000 (98% capacity). Known issues: Gate 6 turnstile malfunction, South medical post missing 2 paramedics, parking lot overflow risk on east side.",
        "zone_hint": "Cloud Spanner",
    },
    {
        "id": "evacuation",
        "title": "Emergency Evacuation Support",
        "icon": "evacuation",
        "color": "red",
        "description": "Provide real-time evacuation guidance, assembly point coordination, emergency communication, and mass egress management.",
        "placeholder": "Describe the evacuation scenario: trigger (fire, bomb threat, crowd crush, structural), area affected, current crowd locations, exits available, PA status, emergency services ETA.",
        "example": "Fire alarm triggered in East Stand concourse Level 2. Smoke visible. 12,000 fans in East Stand. Gates 5–8 are primary exits. PA system is active. Fire brigade ETA 6 minutes. Match suspended.",
        "zone_hint": "Cloud Functions",
    },
    {
        "id": "maintenance",
        "title": "Venue Maintenance Planning",
        "icon": "maintenance",
        "color": "slate",
        "description": "Plan and prioritise venue maintenance tasks, manage equipment failures, coordinate repair crews, and ensure venue compliance for match days.",
        "placeholder": "Describe the maintenance issue: system affected (electrical, plumbing, structural, HVAC, lighting, scoreboard), urgency, impact on operations, crew availability.",
        "example": "Scoreboard display failing on South end — 30% of LED matrix unresponsive. Match starts in 4 hours. Venue tech crew of 3 available. Replacement parts in stadium storage. Backup display available but lower resolution.",
        "zone_hint": "Cloud Build",
    },
]

# Index domains by ID for fast lookup
DOMAIN_BY_ID: dict[str, dict] = {d["id"]: d for d in OPERATIONAL_DOMAINS}

# ---------------------------------------------------------------------------
# Domain-specific system prompts for Gemini
# ---------------------------------------------------------------------------

_DOMAIN_SYSTEM_PROMPTS: dict[str, str] = {
    "crowd_congestion": """You are StadiumIQ's Crowd Management AI Director for FIFA World Cup 2026.
Your role: provide immediate, specific crowd control guidance that operations staff can execute RIGHT NOW.
Guidelines:
- Recommend specific staff redeployment numbers and locations
- Provide queue management tactics (lane separation, barrier placement, steward positioning)
- Give crowd communication messaging for PA/digital signage
- Set clear escalation triggers (when to call for backup/police)
- Always reference FIFA 2026 crowd safety standards (1 steward per 150 fans in normal conditions, 1:75 in high-density)
Format: Start with IMMEDIATE ACTION, then SHORT-TERM PLAN, then ESCALATION TRIGGER.""",

    "ai_recommendations": """You are StadiumIQ's Chief AI Operations Director for FIFA World Cup 2026.
Your role: provide prioritised, actionable operational recommendations for stadium management teams.
Guidelines:
- Prioritise recommendations by urgency (P1 Critical, P2 High, P3 Medium)
- Be specific about WHO does WHAT and WHEN
- Account for FIFA event protocols and fan safety standards
- Reference specific zones, gates, or sections where relevant
- Provide a 3-priority action list the Ops Director can brief their team on immediately
Format: P1 → P2 → P3 with clear owner and timeframe for each.""",

    "security_deployment": """You are StadiumIQ's Security Operations AI Director for FIFA World Cup 2026.
Your role: provide precise security deployment and incident response guidance.
Guidelines:
- Follow FIFA security protocols (threat level Red/Amber/Green framework)
- Specify exact cordon perimeters and exclusion zones
- Coordinate with local law enforcement integration points
- Provide crowd communication scripts for security incidents
- Never escalate unnecessarily — proportional response is critical
- Include comms channel recommendations (which radio channel, who is incident commander)
Format: THREAT ASSESSMENT → IMMEDIATE DEPLOYMENT → COMMS PROTOCOL → ESCALATION CRITERIA.""",

    "medical_response": """You are StadiumIQ's Medical Response AI Director for FIFA World Cup 2026.
Your role: provide immediate medical response coordination guidance.
Guidelines:
- Follow PHEM (Pre-Hospital Emergency Medicine) protocols for mass gatherings
- Specify AED locations, medical post numbers, and ambulance access routes
- Coordinate stadium medical team with external emergency services
- Provide crowd management around incident scene (clear 3m radius minimum)
- Flag when to activate stadium's Major Incident Plan
- Include communication with match officials if play should be stopped
Format: IMMEDIATE RESPONSE → RESOURCE DEPLOYMENT → EXTERNAL SERVICES COORDINATION → DOCUMENTATION.""",

    "staff_allocation": """You are StadiumIQ's Workforce Operations AI Director for FIFA World Cup 2026.
Your role: optimise staff and volunteer allocation across stadium zones in real time.
Guidelines:
- Apply FIFA recommended ratios (1 steward:150 fans standard, 1:75 high density, 1:50 standing)
- Prioritise reallocation from low-density to high-density zones
- Account for break rotations (staff must not work more than 4 hours without a 30-min break)
- Consider travel time between zones when calculating reallocation feasibility
- Identify volunteer vs. paid staff and what tasks each can perform
Format: CURRENT GAP ANALYSIS → REALLOCATION PLAN → RESERVE ACTIVATION → TIMELINE.""",

    "fan_assistance": """You are StadiumIQ's Fan Experience AI Director for FIFA World Cup 2026.
Your role: resolve fan assistance situations with empathy and operational efficiency.
Guidelines:
- Accessibility: always prioritise dignity and FIFA's accessibility standards
- Lost children: activate stadium lost child protocol immediately
- Language barriers: specify which translation resources are available at the venue
- Always give the fan a named contact person and location to go to
- For escalated situations, specify which supervisor level to involve
- Keep solutions within 5 minutes resolution time where possible
Format: IMMEDIATE RESOLUTION → SUPPORT RESOURCES → FOLLOW-UP ACTION.""",

    "gate_optimization": """You are StadiumIQ's Gate Operations AI Director for FIFA World Cup 2026.
Your role: maximise gate throughput and eliminate bottlenecks before they cause crowd safety risks.
Guidelines:
- Calculate throughput gaps (target rate vs actual rate vs fans remaining)
- Recommend gate opening sequences and lane configurations
- Specify steward deployment at bottleneck points (document check, bag search, ticket scan)
- Advise on digital signage and PA messaging to redistribute fan flow
- Set amber and red alert thresholds (e.g., amber = 30 min to kickoff with >5,000 fans queued)
Format: THROUGHPUT ANALYSIS → REDISTRIBUTION PLAN → STAFFING CHANGES → FAN COMMUNICATION.""",

    "parking_management": """You are StadiumIQ's Transportation & Parking AI Director for FIFA World Cup 2026.
Your role: manage vehicle flow, parking allocation, and post-match egress to prevent gridlock.
Guidelines:
- Implement dynamic lot routing (redirect from full lots to available lots with signage)
- Coordinate shuttle bus frequency and additional runs
- Stagger post-match egress waves (VIP first, then sections sequentially)
- Coordinate with local traffic authority for signal timing
- Specify parking lot marshal positions and communication channels
Format: CAPACITY STATUS → DIVERSION PLAN → SHUTTLE COORDINATION → POST-MATCH EGRESS SEQUENCE.""",

    "food_inventory": """You are StadiumIQ's Catering & Inventory AI Director for FIFA World Cup 2026.
Your role: prevent stock-outs, manage replenishment, and maintain food service quality during high-demand periods.
Guidelines:
- Calculate time-to-stockout based on current consumption rate
- Prioritise replenishment by demand and lead time
- Identify substitution options for out-of-stock items
- Advise on pricing adjustments or portion management if needed
- Coordinate with back-of-house logistics team
- Specify food safety compliance requirements (temperature checks, expiry)
Format: STOCK STATUS ASSESSMENT → IMMEDIATE REPLENISHMENT ORDERS → SUBSTITUTION OPTIONS → PREVENTION FOR NEXT MATCH.""",

    "weather_impact": """You are StadiumIQ's Weather & Safety AI Director for FIFA World Cup 2026.
Your role: assess weather threats and provide specific operational protocols to protect fan safety.
Guidelines:
- Apply FIFA's lightning protocol: suspend play if lightning within 8 miles, evacuate open areas
- Heat: WBGT > 28°C requires enhanced medical readiness; > 32°C consider play suspension
- Heavy rain: slip-and-fall risk in concourses, drainage monitoring, ponding alerts
- High wind: structural checks on temporary structures, signage, roof edges
- Always give the time window for action (e.g., "you have 18 minutes before lightning arrives")
- Specify shelter locations and fan communication scripts
Format: THREAT ASSESSMENT → TIME WINDOW → IMMEDIATE PROTOCOLS → FAN COMMUNICATION SCRIPT.""",

    "match_readiness": """You are StadiumIQ's Match-Day Readiness AI Director for FIFA World Cup 2026.
Your role: conduct a comprehensive pre-match readiness assessment and issue a GO/HOLD recommendation.
Guidelines:
- Assess all 8 operational domains: Security, Medical, Crowd, Catering, Transport, Broadcast, Communications, Venue
- Assign a RAG (Red/Amber/Green) status to each domain
- Identify the top 3 risks that could affect match start
- Provide specific remediation actions with responsible owners and deadlines
- Issue a final GO (all Green), CONDITIONAL GO (Amber items have mitigations), or HOLD (Red items unresolved) recommendation
Format: DOMAIN STATUS TABLE → TOP 3 RISKS → REMEDIATION ACTIONS → GO/HOLD RECOMMENDATION.""",

    "evacuation": """You are StadiumIQ's Emergency Response AI Director for FIFA World Cup 2026.
Your role: provide immediate, life-saving evacuation guidance that can be acted upon in seconds.
Guidelines:
- Prioritise safe crowd movement ABOVE ALL ELSE — prevent crowd crush at exits
- Specify which exits to open, which to avoid, in what sequence
- Provide the PA announcement script to read IMMEDIATELY
- Coordinate with emergency services (who calls who, on which channel)
- Specify assembly points and how to account for fans (wristband scanning)
- Flag any special populations (disabled fans, children, medical) needing assisted evacuation
CRITICAL: Lead with the single most important action to take RIGHT NOW.
Format: IMMEDIATE ACTION (do this NOW) → EXIT SEQUENCE → PA SCRIPT → EMERGENCY SERVICES BRIEF → ASSEMBLY POINT PROTOCOL.""",

    "maintenance": """You are StadiumIQ's Venue Maintenance AI Director for FIFA World Cup 2026.
Your role: prioritise maintenance tasks, assess match-day impact, and coordinate repair resources efficiently.
Guidelines:
- Assess if the issue affects match-day operations (critical path vs non-critical)
- Provide a repair plan with estimated time to fix
- Identify workarounds if repair cannot be completed before match
- Specify safety implications and whether a FIFA venue inspection is required
- Coordinate with venue technical team and external contractors
- Flag any items requiring FIFA technical delegate approval
Format: CRITICALITY ASSESSMENT → REPAIR PLAN → WORKAROUND OPTIONS → SAFETY IMPLICATIONS → RESOURCE REQUIREMENTS.""",
}

# ---------------------------------------------------------------------------
# Fallback responses for each domain (when Gemini API unavailable)
# ---------------------------------------------------------------------------

_DOMAIN_FALLBACKS: dict[str, list[str]] = {
    "crowd_congestion": [
        "IMMEDIATE ACTION: Deploy 6 additional stewards to the congested gate — position 2 at funnel entry, 2 at document check, 2 at turnstile lanes. Open all available lanes immediately.",
        "SHORT-TERM PLAN: Activate PA messaging to redirect fans to adjacent gates with spare capacity. Update digital wayfinding signs on concourse approach routes.",
        "ESCALATION TRIGGER: If queue does not reduce by 25% within 10 minutes, or if fans begin to push, call Duty Manager and request police attendance at the gate.",
    ],
    "ai_recommendations": [
        "P1 CRITICAL: Verify all emergency exits are unobstructed and access control is operational across all gates. Deploy Duty Safety Officer to walk the perimeter now.",
        "P2 HIGH: Brief medical teams on projected crowd density — pre-position additional first aid resources at high-density concourses and standing areas.",
        "P3 MEDIUM: Confirm catering and merchandise staffing ratios match expected attendance. Activate contingency staffing if attendance is tracking above forecast.",
    ],
    "security_deployment": [
        "THREAT ASSESSMENT: Treat as Amber until threat is confirmed or cleared. Establish a 20m exclusion zone around the reported location. Do not allow public access.",
        "IMMEDIATE DEPLOYMENT: Move 4 security officers to cordon positions. Appoint an Incident Commander. Notify police via Control Room on designated security channel.",
        "COMMS PROTOCOL: Do not make PA announcements about the specific incident — this can cause panic. Use coded language with stewards. Await police advice before wider announcement.",
    ],
    "medical_response": [
        "IMMEDIATE RESPONSE: Dispatch nearest AED and trained first aider to patient location immediately. Clear 3-metre radius around patient to allow treatment space.",
        "RESOURCE DEPLOYMENT: Alert medical post to prepare ambulance access route. Notify stadium Medical Director. Assign one steward as a runner to guide paramedics from Gate to location.",
        "EXTERNAL COORDINATION: If cardiac arrest is confirmed, ensure ambulance is pre-positioned at nearest access gate. Stadium Medical Director has authority to suspend play if needed.",
    ],
    "staff_allocation": [
        "CURRENT GAP ANALYSIS: Calculate the shortfall: compare current stewards in zone against 1:150 ratio for standard areas, 1:75 for high-density. Identify zones with surplus staff first.",
        "REALLOCATION PLAN: Move surplus stewards from low-density zones (typically outer perimeter) to the understaffed zone. Allow 10 minutes travel time for reallocation.",
        "RESERVE ACTIVATION: If internal reallocation is insufficient, activate reserve steward pool. Brief them on zone assignment and radio channel before deploying.",
    ],
    "fan_assistance": [
        "IMMEDIATE RESOLUTION: Assign a dedicated fan assistance steward to accompany the family. Contact Accessibility Coordinator via radio to identify nearest wheelchair-accessible route and seating.",
        "SUPPORT RESOURCES: Locate nearest British Sign Language (BSL) or communication board resource at the info booth. Stadium accessibility guide is available in 12 languages.",
        "FOLLOW-UP ACTION: Document the accessibility gap for this route. Raise with venue operations manager post-match to ensure alternative routing is available at next event.",
    ],
    "gate_optimization": [
        "THROUGHPUT ANALYSIS: Calculate fans remaining ÷ available minutes = required throughput rate. If gap >20% between actual and required, immediate action is needed.",
        "REDISTRIBUTION PLAN: Open all available lanes at overloaded gates. Issue PA and digital signage directing fans to underutilised gates — use specific gate numbers and estimated wait times.",
        "FAN COMMUNICATION: PA script: 'Attention fans — Gate [X] is experiencing high volume. Gates [Y] and [Z] are open with minimal wait times. Please use the nearest available gate.'",
    ],
    "parking_management": [
        "CAPACITY STATUS: Close full lots to new arrivals immediately and post FULL signage at all entrance approaches. Update digital variable message signs on approach roads.",
        "DIVERSION PLAN: Redirect arriving vehicles to available overflow lots using marshal-guided lanes. Provide clear distances and estimated walk times in fan communications.",
        "POST-MATCH EGRESS: Implement wave release — VIP lots first, then lots in sequence. Do not open all lots simultaneously — staggers traffic and prevents gridlock at main exits.",
    ],
    "food_inventory": [
        "STOCK STATUS: Items with <20% stock and >90 minutes of match time remaining are at critical risk of stock-out. Trigger emergency replenishment for all such items immediately.",
        "IMMEDIATE REPLENISHMENT: Contact back-of-house logistics for fastest available delivery to the affected concession point. Estimated cart delivery time should be under 15 minutes.",
        "SUBSTITUTION OPTIONS: Identify the nearest concession stand with the same item and arrange inter-stand transfer. Update menu boards to reflect any temporary unavailability.",
    ],
    "weather_impact": [
        "THREAT ASSESSMENT: Activate weather monitoring protocol. Assign a designated weather watcher with real-time lightning tracker and direct line to Duty Manager.",
        "IMMEDIATE PROTOCOLS: If lightning detected within 8 miles: notify Match Commissioner, prepare for possible play suspension, open undercover areas for fan shelter, brief medical team.",
        "FAN COMMUNICATION SCRIPT: 'Attention fans — due to adverse weather conditions, we are [suspending play / asking all fans to move to covered areas]. Please follow steward instructions.'",
    ],
    "match_readiness": [
        "DOMAIN STATUS: Conduct a rapid status check across Security (GREEN), Medical (AMBER — staffing at 85%), Crowd (GREEN), Catering (GREEN), Transport (AMBER — parking approaching capacity).",
        "TOP 3 RISKS: 1. Medical staffing below target — activate standby paramedics now. 2. Parking overflow imminent — open overflow lot D pre-emptively. 3. Gate 6 turnstile fault — open manual lane.",
        "GO/CONDITIONAL GO RECOMMENDATION: CONDITIONAL GO — proceed with match subject to medical staffing being resolved within 30 minutes and overflow parking activated. Assign owner for each item.",
    ],
    "evacuation": [
        "IMMEDIATE ACTION: Sound the evacuation alarm NOW. Announce on PA: 'Ladies and gentlemen, please evacuate the stadium calmly using the nearest marked exit. Do not run. Follow steward instructions.'",
        "EXIT SEQUENCE: Open all emergency exits. Prioritise accessible exits first. Avoid directing crowds to the area of the incident — route fans to assembly points on the opposite side.",
        "EMERGENCY SERVICES BRIEF: Incident Commander calls emergency services on direct line. Provide: location, nature of incident, estimated crowd size, which exits are active, current assembly points.",
    ],
    "maintenance": [
        "CRITICALITY ASSESSMENT: Determine if the issue impacts fan safety, match play, or broadcast. Safety-critical items require immediate repair or match hold. Cosmetic issues can be deferred.",
        "REPAIR PLAN: Dispatch venue technical team to assess immediately. Establish a realistic time-to-fix estimate. If repair cannot be completed before match, implement the identified workaround.",
        "SAFETY IMPLICATIONS: If the issue involves electrical, structural, or crowd safety systems — notify the FIFA Technical Delegate and Venue General Manager immediately. Do not proceed without sign-off.",
    ],
}


def _call_gemini(api_key: str, system_prompt: str, user_message: str) -> str:
    """Attempt Gemini API call, trying new SDK then legacy SDK."""
    try:
        from google import genai as genai_new  # type: ignore[import]
        client = genai_new.Client(api_key=api_key)
        full_prompt = system_prompt + "\n\n---\n\nSITUATION REPORT:\n" + user_message
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=full_prompt,
        )
        return response.text.strip()
    except (ImportError, AttributeError):
        import google.generativeai as genai_old  # type: ignore[import]
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_message)
        return response.text.strip()


def _get_fallback_response(domain_id: str, domain_title: str) -> dict[str, Any]:
    """Generates the structured fallback guidance payload for a given domain."""
    fallback = _DOMAIN_FALLBACKS.get(domain_id, _DOMAIN_FALLBACKS["ai_recommendations"])
    return {
        "response": "\n\n".join(fallback),
        "domain_title": domain_title,
        "source": "fallback",
    }


def query_ai_console(domain_id: str, situation: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Query the AI console for domain-specific stadium operations guidance.

    Args:
        domain_id:  One of the 13 operational domain IDs.
        situation:  Free-text description of the situation from operations staff.
        context:    Optional dict with additional structured context
                    (venue, crowd_size, time_to_kickoff, etc.)

    Returns:
        dict with guidance details.
    """
    domain = DOMAIN_BY_ID.get(domain_id, DOMAIN_BY_ID["ai_recommendations"])
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if context:
        context_block = "\nADDITIONAL CONTEXT:\n" + "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}" for k, v in context.items() if v
        )
        full_situation = situation + context_block
    else:
        full_situation = situation

    if not api_key:
        return _get_fallback_response(domain_id, domain["title"])

    try:
        system_prompt = _DOMAIN_SYSTEM_PROMPTS.get(domain_id, _DOMAIN_SYSTEM_PROMPTS["ai_recommendations"])
        raw = _call_gemini(api_key, system_prompt, full_situation)
        return {
            "response": raw,
            "domain_title": domain["title"],
            "source": "gemini",
        }
    except Exception as exc:
        logger.warning("Gemini AI query failed (%s) — using fallback.", exc)
        return _get_fallback_response(domain_id, domain["title"])


def _build_gemini_prompt(values: dict[str, Any], predicted_cost: float) -> str:
    """Build a post-prediction Gemini prompt with full stadium operational context."""
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

    return f"""You are StadiumIQ, an AI Stadium Operations Director for FIFA World Cup 2026.

OPERATIONAL ASSESSMENT RESULTS:
- Zone: {zone_display}
- Venue: {venue_display}
- Crowd Capacity Load: {memory:.0f}%
- System Activity Level: {cpu:.0f}%
- Fan Arrival Flow: {network_in:.1f} GB/hr
- Fan Exit/Egress Flow: {network_out:.1f} GB/hr
- Resource Volume: {qty:,.0f} {unit}
- Operational Window: {start} to {end}
- Estimated Operational Cost: INR {predicted_cost:,.2f}

Based on these operational metrics, provide exactly 3 specific, immediately actionable recommendations for the stadium operations team. Each must:
1. Address a real concern suggested by the metrics
2. Be specific (name the action, the person/team responsible, and the timeframe)
3. Be 1-2 sentences maximum

Respond as a valid JSON array with exactly 3 strings:
["recommendation 1", "recommendation 2", "recommendation 3"]"""


def get_ai_recommendations(values: dict[str, Any], predicted_cost: float) -> dict[str, Any]:
    """Generate post-prediction AI recommendations (called from /predict route)."""
    zone_raw = str(values.get("service_name", ""))
    venue_raw = str(values.get("region", ""))
    zone_display = ZONE_ALIASES.get(zone_raw, zone_raw)
    venue_display = VENUE_ALIASES.get(venue_raw, venue_raw)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    def _fallback_recs():
        cpu = float(values.get("cpu", 50) or 50)
        memory = float(values.get("memory", 50) or 50)
        network_out = float(values.get("network_out", 0) or 0)
        if memory >= 80 or cpu >= 80:
            return _DOMAIN_FALLBACKS["crowd_congestion"]
        if network_out > 200:
            return _DOMAIN_FALLBACKS["parking_management"]
        return _DOMAIN_FALLBACKS["ai_recommendations"]

    if not api_key:
        return {
            "recommendations": _fallback_recs(),
            "source": "fallback",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }
    try:
        prompt = _build_gemini_prompt(values, predicted_cost)
        raw = _call_gemini(api_key, _DOMAIN_SYSTEM_PROMPTS["ai_recommendations"], prompt)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        recommendations = json.loads(raw)
        if not isinstance(recommendations, list):
            raise ValueError("Expected JSON array")
        recommendations = [str(r) for r in recommendations[:3]]
        while len(recommendations) < 3:
            recommendations.extend(_fallback_recs()[:3 - len(recommendations)])
        return {
            "recommendations": recommendations,
            "source": "gemini",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }
    except Exception as exc:
        logger.warning("Gemini post-prediction call failed (%s).", exc)
        return {
            "recommendations": _fallback_recs(),
            "source": "fallback",
            "zone_display": zone_display,
            "venue_display": venue_display,
        }


def get_stadium_status() -> dict[str, Any]:
    """Return simulated live stadium status for the status bar and ops hub."""
    ts = int(time.time())
    rng = random.Random(ts // 30)

    venues = [
        ("MetLife Stadium (NJ/NY)",      rng.randint(55, 97)),
        ("AT&T Stadium (Dallas)",         rng.randint(40, 95)),
        ("SoFi Stadium (Los Angeles)",    rng.randint(30, 92)),
        ("Hard Rock Stadium (Miami)",     rng.randint(60, 99)),
        ("BC Place (Vancouver)",          rng.randint(45, 88)),
        ("Mercedes-Benz Stadium (Atlanta)", rng.randint(50, 94)),
        ("Arrowhead Stadium (Kansas City)", rng.randint(35, 85)),
        ("NRG Stadium (Houston)",         rng.randint(55, 96)),
    ]

    statuses = []
    for venue, capacity in rng.sample(venues, 4):
        alert = "NOMINAL"
        alert_class = "ok"
        if capacity >= 90:
            alert = "HIGH DENSITY"
            alert_class = "warn"
        if capacity >= 96:
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
