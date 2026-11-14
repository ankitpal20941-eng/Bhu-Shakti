"""Exposure, vulnerability and operational priority.

Hazard answers "how likely is instability here". Priority answers "where should
authority act first". They are deliberately separate and separately weighted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..domain import PriorityLevel, PRIORITY_LABELS, priority_level_for
from . import params as P


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class ExposureResult:
    score: float
    counts: dict[str, int]
    road_km_at_risk: float
    population_exposed: int | None
    assets: list[dict[str, Any]]
    method: str
    notes: list[str]


def compute_exposure(
    zone: Any,
    *,
    assets: list[dict[str, Any]],
    road_segments: list[dict[str, Any]],
    buffer_km: float = P.ZONE_BUFFER_KM,
) -> ExposureResult:
    """Proximity-buffer exposure analysis around the unit centroid.

    Method is explicitly a centroid buffer (an approximation for irregular units);
    the buffer radius is configurable and reported with the result.
    """
    counts = {"bridges": 0, "hospitals": 0, "schools": 0, "settlements": 0, "other": 0}
    population = 0
    population_known = False
    nearby: list[dict[str, Any]] = []
    bbox = zone.bbox_json or {}
    for asset in assets:
        inside = (
            bbox.get("min_lat") is not None
            and bbox["min_lat"] <= asset["lat"] <= bbox.get("max_lat", asset["lat"])
            and bbox.get("min_lon", 0) <= asset["lon"] <= bbox.get("max_lon", asset["lon"])
        )
        distance = 0.0 if inside else haversine_km(zone.centroid_lat, zone.centroid_lon,
                                                   asset["lat"], asset["lon"])
        if not inside and distance > buffer_km:
            continue
        kind = asset.get("kind", "other")
        if kind in counts:
            counts[kind] += 1
        else:
            counts["other"] += 1
        if asset.get("population_estimate"):
            population_known = True
            population += int(asset["population_estimate"])
        nearby.append({**asset, "distance_km": round(distance, 2)})

    road_km = 0.0
    for segment in road_segments:
        distance = haversine_km(zone.centroid_lat, zone.centroid_lon,
                                segment.get("lat", zone.centroid_lat), segment.get("lon", zone.centroid_lon))
        if distance <= buffer_km:
            road_km += float(segment.get("length_km") or 0.0)

    raw = (
        counts["bridges"] * P.EXPOSURE_WEIGHTS["bridges"]
        + counts["hospitals"] * P.EXPOSURE_WEIGHTS["hospitals"]
        + counts["schools"] * P.EXPOSURE_WEIGHTS["schools"]
        + counts["settlements"] * P.EXPOSURE_WEIGHTS["settlements"]
        + road_km * P.EXPOSURE_WEIGHTS["road_km"]
        + (population / 1000.0) * P.EXPOSURE_WEIGHTS["population"]
    )
    score = 100.0 * (1.0 - math.exp(-raw / P.EXPOSURE_NORMALISER))
    nearby.sort(key=lambda a: a["distance_km"])
    return ExposureResult(
        score=round(score, 2),
        counts=counts,
        road_km_at_risk=round(road_km, 2),
        population_exposed=population if population_known else None,
        assets=nearby,
        method=(
            f"assets inside the unit polygon plus a {buffer_km} km centroid buffer; "
            f"saturating normaliser {P.EXPOSURE_NORMALISER}"
        ),
        notes=[
            "Exposure is an indicator of assets near the unit, not a damage estimate.",
            "Population figures are dataset estimates, not a census count of people at risk.",
        ],
    )


def compute_vulnerability(
    *,
    exposure: ExposureResult,
    district_asset_max: dict[str, int],
    nearest_hospital_km: float | None,
    landcover: str | None,
) -> dict[str, Any]:
    """Assumption-based vulnerability index with explicit weights and inputs."""
    settlement_density = min(1.0, exposure.counts["settlements"] / max(1, district_asset_max.get("settlements", 1)))
    road_dependency = min(1.0, exposure.road_km_at_risk / 6.0)
    emergency_gap = 0.0 if nearest_hospital_km is None else min(1.0, nearest_hospital_km / 25.0)
    sensitivity = P.LANDSLIDE_TYPE_FACTORS.get((landcover or "unknown").lower(), 0.35)
    population_share = min(1.0, (exposure.population_exposed or 0) / 20_000.0)

    parts = {
        "settlement_density": round(settlement_density, 3),
        "road_dependency": round(road_dependency, 3),
        "emergency_access_gap": round(emergency_gap, 3),
        "landcover_sensitivity": round(sensitivity, 3),
        "population_share": round(population_share, 3),
    }
    score = 100.0 * sum(P.VULNERABILITY_WEIGHTS[k] * v for k, v in parts.items())
    return {
        "score": round(min(100.0, score), 2),
        "components": parts,
        "weights": P.VULNERABILITY_WEIGHTS,
        "nearest_hospital_km": (round(nearest_hospital_km, 2) if nearest_hospital_km is not None else None),
        "note": "Assumption-based, configurable indicators. Not a validated social-vulnerability model.",
    }


def compute_priority(hazard_index: float, exposure_score: float, vulnerability_score: float) -> dict[str, Any]:
    score = (
        P.PRIORITY_WEIGHTS["hazard"] * hazard_index
        + P.PRIORITY_WEIGHTS["exposure"] * exposure_score
        + P.PRIORITY_WEIGHTS["vulnerability"] * vulnerability_score
    )
    level = priority_level_for(score)
    return {
        "score": round(score, 2),
        "level": level.value,
        "label": PRIORITY_LABELS[level],
        "weights": P.PRIORITY_WEIGHTS,
        "contributions": {
            "hazard": round(P.PRIORITY_WEIGHTS["hazard"] * hazard_index, 2),
            "exposure": round(P.PRIORITY_WEIGHTS["exposure"] * exposure_score, 2),
            "vulnerability": round(P.PRIORITY_WEIGHTS["vulnerability"] * vulnerability_score, 2),
        },
        "formula": "priority = 0.60*hazard + 0.25*exposure + 0.15*vulnerability",
        "note": "Operational ranking. Not a probability and not an official warning level.",
    }


PRIMARY_ACTIONS = {
    PriorityLevel.P1: (
        "Immediate field inspection; alert district control room; pre-position response team; "
        "prepare an alert for authority approval. Do not publish without approval."
    ),
    PriorityLevel.P2: (
        "Urgent inspection within 24 hours; confirm access and verify field reports; "
        "review alert candidate with the district authority."
    ),
    PriorityLevel.P3: "Monitor; schedule inspection within the week and re-check after rainfall.",
    PriorityLevel.P4: "Routine monitoring on the next scheduled cycle.",
}


def recommended_action(priority_level: str, hazard_level: str) -> str:
    if hazard_level == "CRITICAL" and priority_level != "P1":
        return (
            "Hazard is critical but exposure is limited. Verify conditions on site and keep the "
            "alert candidate under review with the authority."
        )
    try:
        return PRIMARY_ACTIONS[PriorityLevel(priority_level)]
    except (ValueError, KeyError):
        return PRIMARY_ACTIONS[PriorityLevel.P4]
