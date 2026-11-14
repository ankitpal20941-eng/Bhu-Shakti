"""Smart Emergency Response Optimizer Engine.

Ranks and allocates field inspection and emergency response teams to incidents:
- Multi-criteria decision model (distance, road accessibility, team availability, skill match, workload)
- Explainable score decomposition and transparent reasoning
- Explicit admin override mechanism
"""

from __future__ import annotations

import math
from typing import Any

from .impact import haversine_distance_km

# Weight factors for composite ranking score (0 to 100)
WEIGHTS = {
    "distance": 0.30,
    "road_access": 0.25,
    "skill_match": 0.25,
    "workload": 0.20,
}


def rank_field_teams_for_incident(
    incident: dict[str, Any],
    teams: list[dict[str, Any]],
    blocked_road_corridors: set[str],
) -> list[dict[str, Any]]:
    """Ranks available field teams for a target incident, generating explainable rationale."""
    inc_lat = float(incident.get("lat") or 0.0)
    inc_lon = float(incident.get("lon") or 0.0)
    inc_hazard_type = incident.get("hazard_type", "SLOPE_MOVEMENT")
    inc_priority = incident.get("priority", "P2")

    ranked = []

    for team in teams:
        team_id = team.get("id")
        team_code = team.get("team_code", f"TEAM-{team_id}")
        t_lat = float(team.get("base_lat") or inc_lat + 0.05)
        t_lon = float(team.get("base_lon") or inc_lon + 0.05)
        status = team.get("status", "AVAILABLE")
        spec = team.get("specialization", "GEOTECHNICAL_ASSESSMENT")
        active_assignments = int(team.get("current_active_assignments") or 0)

        # 1. Distance & transit score (100 is closest, 0 is > 50km)
        dist_km = haversine_distance_km(t_lat, t_lon, inc_lat, inc_lon)
        dist_score = max(0.0, min(100.0, 100.0 - (dist_km * 2.0)))
        transit_min = int((dist_km / 35.0) * 60) + 10

        # 2. Road accessibility score
        # If roads between team and incident are blocked, penalize
        is_accessible = True
        road_score = 100.0
        for blocked in blocked_road_corridors:
            if blocked.lower() in team.get("name", "").lower():
                is_accessible = False
                road_score = 30.0
                transit_min += 45

        # 3. Skill match score
        skill_score = 70.0
        if inc_hazard_type in {"ROCKFALL", "SLOPE_MOVEMENT"} and spec == "GEOTECHNICAL_ASSESSMENT":
            skill_score = 100.0
        elif inc_hazard_type in {"DEBRIS_FLOW", "SUBSIDENCE"} and spec in {"SEARCH_AND_RESCUE", "DRONE_RECONNAISSANCE"}:
            skill_score = 95.0
        elif spec == "DRONE_RECONNAISSANCE":
            skill_score = 85.0

        # 4. Workload penalty
        workload_score = max(0.0, 100.0 - (active_assignments * 30.0))
        if status != "AVAILABLE":
            workload_score = 10.0

        composite = (
            dist_score * WEIGHTS["distance"] +
            road_score * WEIGHTS["road_access"] +
            skill_score * WEIGHTS["skill_match"] +
            workload_score * WEIGHTS["workload"]
        )

        # Generate human-readable rationale
        reasons = []
        if dist_km < 12.0:
            reasons.append(f"Optimal proximity ({round(dist_km, 1)} km, ~{transit_min} min)")
        else:
            reasons.append(f"Extended travel distance ({round(dist_km, 1)} km)")

        if skill_score >= 95.0:
            reasons.append(f"Direct skill alignment ({spec.replace('_', ' ').title()})")

        if active_assignments == 0 and status == "AVAILABLE":
            reasons.append("Zero current backlog; immediate dispatch ready")
        elif active_assignments > 0:
            reasons.append(f"Active load: {active_assignments} ongoing assignment(s)")

        if not is_accessible:
            reasons.append("Detour required due to blocked road corridor")

        ranked.append({
            "team_id": team_id,
            "team_code": team_code,
            "team_name": team.get("name"),
            "specialization": spec,
            "status": status,
            "estimated_distance_km": round(dist_km, 1),
            "estimated_transit_min": transit_min,
            "road_accessible": is_accessible,
            "score_breakdown": {
                "distance_score": round(dist_score, 1),
                "road_access_score": round(road_score, 1),
                "skill_match_score": round(skill_score, 1),
                "workload_score": round(workload_score, 1),
                "composite_score": round(composite, 1),
            },
            "composite_score": round(composite, 1),
            "recommendation_rationale": "; ".join(reasons),
        })

    ranked.sort(key=lambda r: r["composite_score"], reverse=True)
    for idx, r in enumerate(ranked):
        r["rank"] = idx + 1

    return ranked
