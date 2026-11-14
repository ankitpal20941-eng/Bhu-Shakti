"""Hazard computation: static susceptibility + dynamic trigger + verified field evidence.

SENSE -> PREDICT -> EXPLAIN
The output is an INDEX in [0, 100] and never a probability. Each component keeps
its own contribution so the API can attribute the score (see explain.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import params as P


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def id_threshold_mm_per_h(duration_h: float, regional_factor: float = P.ID_REGIONAL_FACTOR) -> float:
    """Caine (1980) global intensity-duration envelope, regionally scaled."""
    duration_h = max(0.25, float(duration_h))
    return P.ID_A * (duration_h ** P.ID_B) * regional_factor


def aspect_wetness(aspect_deg: float | None) -> float:
    """South/south-west aspects receive more monsoon rain in the NER."""
    if aspect_deg is None:
        return 0.0
    return math.cos(math.radians(aspect_deg - 200.0))


def landcover_factor(code: str | None) -> float:
    return P.LANDSLIDE_TYPE_FACTORS.get((code or "unknown").lower(), 0.35)


def geology_factor(code: str | None) -> float:
    return P.GEOLOGY_FACTORS.get((code or "unknown").lower(), 0.40)


def road_cut_factor(proximity_m: float | None) -> float:
    if proximity_m is None:
        return 0.0
    return math.exp(-max(0.0, proximity_m) / 300.0)


@dataclass
class StaticResult:
    index: float
    logit: float
    probability_uncalibrated: float
    terms: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    out_of_domain: bool = False


def static_susceptibility(zone: Any) -> StaticResult:
    """Logistic susceptibility with an exact additive log-odds decomposition."""
    values: dict[str, float | None] = {
        "slope_deg": zone.slope_deg,
        "terrain_ruggedness": zone.terrain_ruggedness,
        "curvature": zone.curvature,
        "elevation_m": zone.elevation_m,
        "twi": zone.twi,
        "aspect_wetness": aspect_wetness(zone.aspect_deg),
        "landcover_factor": landcover_factor(zone.landcover),
        "geology_factor": geology_factor(zone.geology),
        "road_cut_factor": road_cut_factor(zone.road_cut_proximity_m),
    }
    terms: list[dict[str, Any]] = []
    missing: list[str] = []
    z = P.INTERCEPT
    for spec in P.FEATURES:
        raw = values.get(spec.key)
        if raw is None:
            missing.append(spec.key)
            continue
        std = spec.standardise(float(raw))
        term = spec.weight * std
        z += term
        terms.append({
            "key": spec.key,
            "label": spec.label,
            "value": round(float(raw), 4),
            "standardised": round(std, 4),
            "log_odds": round(term, 4),
            "weight": spec.weight,
            "provenance": spec.provenance,
        })
    p = _sigmoid(z)
    ood = (
        (zone.slope_deg is not None and zone.slope_deg > 45)
        or (zone.elevation_m is not None and zone.elevation_m > 3500)
        or len(missing) >= 2
    )
    return StaticResult(
        index=round(100.0 * p, 2),
        logit=round(z, 4),
        probability_uncalibrated=round(p, 4),
        terms=terms,
        missing=missing,
        out_of_domain=ood,
    )


@dataclass
class TriggerResult:
    index: float
    components: dict[str, Any]
    available: bool
    notes: list[str] = field(default_factory=list)


def dynamic_trigger(
    *,
    rainfall_1h: float | None,
    rainfall_6h: float | None,
    rainfall_24h: float | None,
    rainfall_72h: float | None,
    forecast_24h: float | None,
    soil_moisture_pct: float | None,
    month: int,
) -> TriggerResult:
    """Rainfall intensity/duration + antecedent + soil-moisture trigger.

    Ratios compare observed intensity to the regional ID threshold. A ratio of 1.0
    means rainfall is exactly at the prototype threshold; the trigger index is 50
    at that point and rises with log-ratio.
    """
    notes: list[str] = []
    available_inputs = [v for v in (rainfall_1h, rainfall_6h, rainfall_24h, rainfall_72h) if v is not None]
    if not available_inputs:
        return TriggerResult(index=0.0, components={"status": "NO_RAINFALL_INPUT"}, available=False,
                             notes=["No rainfall input available; trigger component omitted from hazard."])

    def ratio(total_mm: float | None, hours: float) -> float | None:
        if total_mm is None:
            return None
        return (total_mm / hours) / id_threshold_mm_per_h(hours)

    ratios = {
        "r_1h": ratio(rainfall_1h, 1),
        "r_6h": ratio(rainfall_6h, 6),
        "r_24h": ratio(rainfall_24h, 24),
        "r_72h": ratio(rainfall_72h, 72),
        "r_fc24": ratio(forecast_24h, 24),
    }
    weighted = 0.0
    used_weight = 0.0
    for key, weight in P.TRIGGER_WEIGHTS.items():
        value = ratios.get(key)
        if value is None:
            notes.append(f"{key} unavailable")
            continue
        weighted += weight * math.log(max(1e-4, value))
        used_weight += weight
    if used_weight <= 0:
        return TriggerResult(index=0.0, components={"status": "NO_USABLE_RATIO"}, available=False, notes=notes)

    log_ratio = weighted / used_weight
    combined_ratio = math.exp(log_ratio)
    trigger = _sigmoid(P.TRIGGER_LOGIT_SCALE * log_ratio)

    soil = _clamp((soil_moisture_pct - P.SOIL_MOISTURE_FLOOR_PCT) /
                  (P.SOIL_MOISTURE_CEILING_PCT - P.SOIL_MOISTURE_FLOOR_PCT)) if soil_moisture_pct is not None else None
    if soil is not None:
        trigger = min(1.0, trigger * (1.0 - P.SOIL_MOISTURE_MAX_BOOST + P.SOIL_MOISTURE_MAX_BOOST * 2 * soil))
        notes.append("Soil moisture modifier applied (0-7 cm layer).")
    else:
        notes.append("Soil moisture unavailable; wetness modifier omitted.")

    season_factor = 1.0 if month in P.MONSOON_MONTHS else P.DRY_SEASON_TRIGGER_FACTOR
    trigger *= season_factor
    trigger = _clamp(trigger)

    return TriggerResult(
        index=round(100.0 * trigger, 2),
        available=True,
        components={
            "ratios": {k: (round(v, 3) if v is not None else None) for k, v in ratios.items()},
            "combined_ratio": round(combined_ratio, 3),
            "thresholds_mm_per_h": {
                "1h": round(id_threshold_mm_per_h(1), 2),
                "6h": round(id_threshold_mm_per_h(6), 2),
                "24h": round(id_threshold_mm_per_h(24), 2),
                "72h": round(id_threshold_mm_per_h(72), 2),
            },
            "soil_moisture_factor": (round(soil, 3) if soil is not None else None),
            "soil_moisture_pct": soil_moisture_pct,
            "season_factor": season_factor,
            "id_source": P.ID_SOURCE,
        },
        notes=notes,
    )


def combine_hazard(static_index: float, trigger_index: float, trigger_available: bool) -> tuple[float, dict[str, Any]]:
    """Multiplicative susceptibility x trigger activation (monotone, bounded).

        hazard = 100 * (S/100) * (0.20 + 0.80 * T/100)

    Terrain susceptibility is a propensity, not a hazard. Dry weather therefore
    yields a low hazard even on steep ground; threshold-exceeding rainfall raises
    it towards the susceptibility ceiling. When rainfall is unavailable a
    documented mid-range assumption (0.5) is applied and coverage is reduced.
    """
    s = _clamp(static_index / 100.0)
    if trigger_available:
        t = _clamp(trigger_index / 100.0)
        multiplier = P.TRIGGER_FLOOR + (1.0 - P.TRIGGER_FLOOR) * t
    else:
        t = 0.0
        multiplier = P.TRIGGER_UNAVAILABLE_MULTIPLIER
    h = s * multiplier
    return round(100.0 * h, 2), {
        "static_index": round(static_index, 2),
        "trigger_index": round(trigger_index, 2) if trigger_available else 0.0,
        "trigger_available": trigger_available,
        "trigger_multiplier": round(multiplier, 4),
        "dynamic_lift_points": round(100.0 * (h - s), 2),
        "formula": "hazard = 100 * (S/100) * (0.20 + 0.80 * T/100)",
    }


def field_evidence_adjustment(verified_reports: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    """Bounded, time-decaying uplift from VERIFIED field reports only.

    Unverified reports never reach this function. Total uplift is capped at 15
    hazard points so a single observation cannot dominate the model.
    """
    now = now or datetime.now(timezone.utc)
    total = 0.0
    items: list[dict[str, Any]] = []
    for report in verified_reports:
        if report.get("status") != "VERIFIED":
            continue
        observed = report.get("observed_at")
        if isinstance(observed, str):
            try:
                observed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            except ValueError:
                continue
        if observed is None:
            continue
        age_days = max(0.0, (now - observed).total_seconds() / 86400.0)
        if age_days > P.FIELD_EVIDENCE_WINDOW_DAYS:
            continue
        base = P.FIELD_EVIDENCE_WEIGHTS.get(report.get("hazard_type", "OTHER"), 2.0)
        decay = 0.5 ** (age_days / P.FIELD_EVIDENCE_HALF_LIFE_DAYS)
        contribution = base * decay
        total += contribution
        items.append({
            "report_id": report.get("id"),
            "hazard_type": report.get("hazard_type"),
            "age_days": round(age_days, 2),
            "base_points": base,
            "decayed_points": round(contribution, 2),
        })
    applied = round(min(P.FIELD_EVIDENCE_MAX_POINTS, total), 2)
    return {
        "raw_points": round(total, 2),
        "applied_points": applied,
        "cap_points": P.FIELD_EVIDENCE_MAX_POINTS,
        "items": items,
        "note": (
            "Verified field evidence only; bounded and time-decayed. Unverified citizen "
            "reports never modify hazard."
        ),
    }


def coverage_and_uncertainty(
    *,
    weather_state: str,
    weather_age_minutes: int | None,
    soil_moisture_present: bool,
    terrain_source: str,
    verified_inventory_count: int,
    landcover_source: str,
    weather_sla_minutes: int = 180,
    out_of_domain: bool = False,
) -> dict[str, Any]:
    """Explicit rule-based data-coverage score. No invented confidence percentages."""
    points = 0
    reasons: list[str] = []
    if weather_state == "LIVE":
        if weather_age_minutes is not None and weather_age_minutes <= weather_sla_minutes:
            points += P.COVERAGE_POINTS["weather_live_fresh"]
            reasons.append("Rainfall: live and within freshness SLA")
        else:
            points += P.COVERAGE_POINTS["weather_live_aged"]
            reasons.append("Rainfall: live but older than the freshness SLA")
    elif weather_state in {"CACHED", "STALE"}:
        points += P.COVERAGE_POINTS["weather_cached"]
        reasons.append(f"Rainfall: {weather_state.lower()} observation")
    else:
        reasons.append("Rainfall: unavailable")

    if soil_moisture_present:
        points += P.COVERAGE_POINTS["soil_moisture_live"]
        reasons.append("Soil moisture: present")
    else:
        reasons.append("Soil moisture: absent")

    if terrain_source and "DEM" in terrain_source:
        points += P.COVERAGE_POINTS["terrain_live"]
        reasons.append("Terrain: derived from a live DEM sampling")
    else:
        reasons.append("Terrain: demo assignment")

    if verified_inventory_count > 0:
        points += P.COVERAGE_POINTS["verified_inventory"]
        reasons.append(f"Historical inventory: {verified_inventory_count} verified event(s) in district")
    else:
        reasons.append("Historical inventory: none available for this district")

    if landcover_source and "simulated" not in landcover_source.lower():
        points += P.COVERAGE_POINTS["landcover_authoritative"]
        reasons.append("Land cover: authoritative")
    else:
        reasons.append("Land cover: demo assignment")

    from ..domain import CoverageLevel

    if points >= P.COVERAGE_HIGH_MIN and weather_state == "LIVE":
        level = CoverageLevel.HIGH
    elif points >= P.COVERAGE_MEDIUM_MIN:
        level = CoverageLevel.MEDIUM
    else:
        level = CoverageLevel.LOW
    if weather_state in {"UNAVAILABLE", "DEGRADED", "SIMULATED", "STALE"} and level == CoverageLevel.HIGH:
        level = CoverageLevel.MEDIUM

    return {
        "level": level.value,
        "points": points,
        "max_points": sum(P.COVERAGE_POINTS.values()),
        "reasons": reasons,
        "out_of_domain": out_of_domain,
        "out_of_domain_note": (
            "Inputs fall outside the range the prototype was designed for; treat the score as unreliable."
            if out_of_domain else ""
        ),
        "method": "rule-based coverage score (params.COVERAGE_POINTS), not a statistical confidence",
    }
