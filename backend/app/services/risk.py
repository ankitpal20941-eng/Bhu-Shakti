"""Risk orchestration: SENSE -> PREDICT -> EXPLAIN -> PRIORITIZE.

Hazard, exposure, vulnerability and operational priority are computed and stored
separately. Scenario runs are stored in the same table but flagged
``is_scenario`` and excluded from every operational query.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain import (
    DataState,
    PriorityLevel,
    RISK_THRESHOLDS,
    RiskLevel,
    risk_level_for,
)
from ..engine import params as P
from ..engine.exposure import (
    compute_exposure,
    compute_priority,
    compute_vulnerability,
    haversine_km,
    recommended_action,
)
from ..engine.explain import explain
from ..engine.hazard import (
    combine_hazard,
    coverage_and_uncertainty,
    dynamic_trigger,
    field_evidence_adjustment,
    static_susceptibility,
)
from ..models import (
    DataSource,
    District,
    FeatureSnapshot,
    InfrastructureAsset,
    LandslideIncident,
    Report,
    RiskAssessment,
    RoadSegment,
    SpatialUnit,
    WeatherForecast,
    WeatherObservation,
)
from . import audit
from .events import bus
from .util import as_utc, iso, minutes_since

DEFAULT_SCENARIO_ASSUMPTIONS = {
    "rainfall_1h": "uniform distribution of scenario 24 h rainfall",
    "rainfall_6h": "uniform distribution of scenario 24 h rainfall",
    "rainfall_72h": "scenario antecedent estimate (2x scenario 24 h)",
    "field_evidence": "verified evidence optionally included",
}


# ---------------------------------------------------------------- lookups
def latest_assessment(db: Session, zone_id: int, *, include_scenario: bool = False) -> RiskAssessment | None:
    stmt = select(RiskAssessment).where(RiskAssessment.zone_id == zone_id)
    if not include_scenario:
        stmt = stmt.where(RiskAssessment.is_scenario.is_(False))
    stmt = stmt.order_by(RiskAssessment.computed_at.desc()).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def latest_assessments(db: Session, zone_ids: Iterable[int]) -> dict[int, RiskAssessment]:
    ids = list(zone_ids)
    if not ids:
        return {}
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.zone_id.in_(ids), RiskAssessment.is_scenario.is_(False))
        .order_by(RiskAssessment.zone_id, RiskAssessment.computed_at.desc())
    )
    out: dict[int, RiskAssessment] = {}
    for row in db.execute(stmt).scalars():
        out.setdefault(row.zone_id, row)
    return out


def latest_weather(db: Session, district_code: str) -> WeatherObservation | None:
    stmt = (
        select(WeatherObservation)
        .where(WeatherObservation.district_code == district_code)
        .order_by(WeatherObservation.observed_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def forecast_horizons(db: Session, district_code: str) -> tuple[dict[int, float], datetime | None]:
    stmt = (
        select(WeatherForecast)
        .where(WeatherForecast.district_code == district_code)
        .order_by(WeatherForecast.issued_at.desc())
    )
    rows = list(db.execute(stmt).scalars())
    if not rows:
        return {}, None
    latest_issued = max(as_utc(r.issued_at) for r in rows)
    out: dict[int, float] = {}
    for row in rows:
        if as_utc(row.issued_at) == latest_issued:
            out.setdefault(row.horizon_h, float(row.rainfall_mm))
    return out, latest_issued


def effective_weather_state(source: DataSource | None, observed_at: datetime | None, now: datetime) -> DataState:
    if observed_at is None:
        return DataState.UNAVAILABLE
    if source is not None and source.state == DataState.SIMULATED:
        return DataState.SIMULATED
    age = minutes_since(observed_at, now) or 0
    sla = source.freshness_sla_min if source else 180
    if age <= sla:
        return DataState.LIVE
    if age <= sla * 6:
        return DataState.STALE
    return DataState.UNAVAILABLE


# ---------------------------------------------------------------- computation
def compute_assessment(
    db: Session,
    zone: SpatialUnit,
    *,
    district: District,
    weather: WeatherObservation | None,
    weather_state: DataState,
    forecasts: dict[int, float],
    forecast_issued_at: datetime | None,
    verified_reports: list[Report],
    assets: list[InfrastructureAsset],
    segments: list[RoadSegment],
    district_settlement_max: int,
    verified_inventory: int,
    now: datetime,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure computation for one unit. Returns everything needed to persist + explain."""
    overrides = overrides or {}
    month = now.month

    rain = {
        "1h": float(weather.rainfall_1h) if weather and weather.rainfall_1h is not None else None,
        "6h": float(weather.rainfall_6h) if weather and weather.rainfall_6h is not None else None,
        "24h": float(weather.rainfall_24h) if weather and weather.rainfall_24h is not None else None,
        "72h": float(weather.rainfall_72h) if weather and weather.rainfall_72h is not None else None,
    }
    soil = float(weather.soil_moisture_pct) if weather and weather.soil_moisture_pct is not None else None
    if overrides:
        rain["24h"] = float(overrides.get("rainfall_24h", rain["24h"] or 0.0))
        rain["1h"] = round(rain["24h"] / 24.0, 2)
        rain["6h"] = round(rain["24h"] / 4.0, 2)
        rain["72h"] = round(rain["24h"] * 2.0, 2)
        soil = float(overrides.get("soil_moisture_pct", soil if soil is not None else 35.0))
        forecasts = {h: float(overrides.get("rainfall_24h", 0.0)) for h in forecasts} or {}

    static = static_susceptibility(zone)
    trigger = dynamic_trigger(
        rainfall_1h=rain["1h"],
        rainfall_6h=rain["6h"],
        rainfall_24h=rain["24h"],
        rainfall_72h=rain["72h"],
        forecast_24h=forecasts.get(24),
        soil_moisture_pct=soil,
        month=month,
    )
    hazard, components = combine_hazard(static.index, trigger.index, trigger.available)

    use_field = overrides.get("use_field_evidence", True) if overrides else True
    reports_payload = [
        {
            "id": r.id,
            "status": r.status,
            "hazard_type": r.hazard_type,
            "observed_at": as_utc(r.observed_at),
        }
        for r in verified_reports
    ]
    if not use_field:
        reports_payload = []
    field = field_evidence_adjustment(reports_payload, now=now)
    adjusted_hazard = min(100.0, hazard + field["applied_points"])
    level = risk_level_for(adjusted_hazard)

    exposure = compute_exposure(
        zone,
        assets=[{"id": a.id, "kind": a.kind, "name": a.name, "lat": a.lat, "lon": a.lon,
                 "population_estimate": a.population_estimate, "source": a.source,
                 "source_state": a.source_state} for a in assets],
        road_segments=[{"id": s.id, "name": s.name, "length_km": s.length_km,
                        "lat": zone.centroid_lat, "lon": zone.centroid_lon} for s in segments],
    )
    nearest_hospital = None
    for asset in assets:
        if asset.kind == "hospital":
            d = haversine_km(zone.centroid_lat, zone.centroid_lon, asset.lat, asset.lon)
            nearest_hospital = d if nearest_hospital is None else min(nearest_hospital, d)
    vulnerability = compute_vulnerability(
        exposure=exposure,
        district_asset_max={"settlements": district_settlement_max},
        nearest_hospital_km=nearest_hospital,
        landcover=zone.landcover,
    )
    priority = compute_priority(adjusted_hazard, exposure.score, vulnerability["score"])

    observed_at = as_utc(weather.observed_at) if weather else None
    coverage = coverage_and_uncertainty(
        weather_state=weather_state.value,
        weather_age_minutes=minutes_since(observed_at, now),
        soil_moisture_present=soil is not None,
        terrain_source=zone.terrain_source,
        verified_inventory_count=verified_inventory,
        landcover_source=zone.landcover_source,
        out_of_domain=static.out_of_domain,
    )

    explanation = explain(
        static=static,
        trigger=trigger,
        component_breakdown=components,
        field_evidence=field,
        exposure={"score": exposure.score},
        vulnerability_score=vulnerability["score"],
        priority=priority,
    )

    inputs = {
        "rainfall": {**rain, "forecast_24h": forecasts.get(24)},
        "soil_moisture_pct": soil,
        "observed_at": iso(observed_at),
        "weather_source_id": weather.source_id if weather else None,
        "weather_source_state": weather_state.value,
        "forecasts": {str(k): v for k, v in sorted(forecasts.items())},
        "forecast_issued_at": iso(forecast_issued_at),
        "trigger": trigger.components,
        "trigger_notes": trigger.notes,
        "static": {
            "index": static.index,
            "logit": static.logit,
            "terms": static.terms,
            "missing": static.missing,
            "intercept": P.INTERCEPT,
        },
        "components": components,
        "field_evidence": {k: v for k, v in field.items() if k != "items"},
        "coverage": coverage,
        "exposure": {
            "score": exposure.score,
            "counts": exposure.counts,
            "road_km_at_risk": exposure.road_km_at_risk,
            "population_exposed": exposure.population_exposed,
            "assets": exposure.assets[:25],
            "method": exposure.method,
            "notes": exposure.notes,
        },
        "vulnerability": vulnerability,
        "priority": priority,
        "verified_inventory_count": verified_inventory,
        "zone": {
            "elevation_m": zone.elevation_m,
            "slope_deg": zone.slope_deg,
            "aspect_deg": zone.aspect_deg,
            "curvature": zone.curvature,
            "terrain_ruggedness": zone.terrain_ruggedness,
            "twi": zone.twi,
            "landcover": zone.landcover,
            "geology": zone.geology,
            "road_cut_proximity_m": zone.road_cut_proximity_m,
            "terrain_source": zone.terrain_source,
            "landcover_source": zone.landcover_source,
            "geology_source": zone.geology_source,
        },
        "recommended_action": recommended_action(priority["level"], level.value),
        "scenario": overrides or None,
        "scenario_assumptions": DEFAULT_SCENARIO_ASSUMPTIONS if overrides else None,
    }

    return {
        "hazard_index": round(adjusted_hazard, 2),
        "hazard_level": level.value,
        "hazard_probability": None,
        "probability_status": "NOT_CALIBRATED",
        "exposure_score": exposure.score,
        "vulnerability_score": vulnerability["score"],
        "priority_score": priority["score"],
        "priority_level": priority["level"],
        "coverage_level": coverage["level"],
        "out_of_domain": bool(static.out_of_domain),
        "inputs": inputs,
        "drivers": explanation,
        "weather_state": weather_state.value,
        "data_age_minutes": minutes_since(observed_at, now),
        "recommended_action": inputs["recommended_action"],
    }


# ---------------------------------------------------------------- orchestration
def recalculate(
    db: Session,
    *,
    district_codes: list[str] | None = None,
    actor: dict[str, Any] | None = None,
    request_id: str = "",
    reason: str = "scheduled risk recalculation",
    scenario: dict[str, Any] | None = None,
    scenario_run_id: int | None = None,
) -> dict[str, Any]:
    """Recompute assessments for the given districts (statewide when None)."""
    now = datetime.now(timezone.utc)
    run_id = f"run-{now.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    is_scenario = scenario is not None

    district_stmt = select(District)
    if district_codes:
        district_stmt = district_stmt.where(District.code.in_(district_codes))
    districts = list(db.execute(district_stmt).scalars())
    if not districts:
        return {"run_id": run_id, "zones_assessed": 0, "districts": [], "error": "no matching districts"}

    assessments: list[RiskAssessment] = []
    new_alerts: list[dict[str, Any]] = []
    level_counts: dict[str, int] = {level.value: 0 for level in RiskLevel}
    priority_counts: dict[str, int] = {level.value: 0 for level in PriorityLevel}
    coverage_counts: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for district in districts:
        zones = list(db.execute(
            select(SpatialUnit).where(SpatialUnit.district_code == district.code)
        ).scalars())
        if not zones:
            continue
        weather = latest_weather(db, district.code)
        source = db.get(DataSource, weather.source_id) if weather else None
        weather_state = effective_weather_state(source, as_utc(weather.observed_at) if weather else None, now)
        forecasts, forecast_issued = forecast_horizons(db, district.code)
        assets = list(db.execute(
            select(InfrastructureAsset).where(InfrastructureAsset.district_code == district.code)
        ).scalars())
        settlements = sum(1 for a in assets if a.kind == "settlements")
        segments_all = list(db.execute(
            select(RoadSegment).join(SpatialUnit, RoadSegment.zone_id == SpatialUnit.id)
            .where(SpatialUnit.district_code == district.code)
        ).scalars())
        segments_by_zone: dict[int, list[RoadSegment]] = {}
        for seg in segments_all:
            segments_by_zone.setdefault(seg.zone_id, []).append(seg)  # type: ignore[arg-type]
        verified_inventory = int(db.execute(
            select(LandslideIncident).where(
                LandslideIncident.district_code == district.code,
                LandslideIncident.verified.is_(True),
            )
        ).scalars().all().__len__())

        reports = list(db.execute(
            select(Report).where(
                Report.district_code == district.code,
                Report.status == "VERIFIED",
                Report.zone_id.is_not(None),
            )
        ).scalars())
        reports_by_zone: dict[int, list[Report]] = {}
        for rep in reports:
            reports_by_zone.setdefault(rep.zone_id, []).append(rep)  # type: ignore[arg-type]

        for zone in zones:
            result = compute_assessment(
                db,
                zone,
                district=district,
                weather=weather,
                weather_state=weather_state,
                forecasts=forecasts,
                forecast_issued_at=forecast_issued,
                verified_reports=reports_by_zone.get(zone.id, []),
                assets=assets,
                segments=segments_by_zone.get(zone.id, []),
                district_settlement_max=max(1, settlements),
                verified_inventory=verified_inventory,
                now=now,
                overrides=scenario,
            )
            row = RiskAssessment(
                zone_id=zone.id,
                run_id=run_id,
                hazard_index=result["hazard_index"],
                hazard_level=result["hazard_level"],
                hazard_probability=None,
                probability_status=result["probability_status"],
                exposure_score=result["exposure_score"],
                vulnerability_score=result["vulnerability_score"],
                priority_score=result["priority_score"],
                priority_level=result["priority_level"],
                coverage_level=result["coverage_level"],
                out_of_domain=result["out_of_domain"],
                model_version=P.MODEL_VERSION,
                inputs=result["inputs"],
                drivers=result["drivers"],
                computed_at=now,
                data_age_minutes=result["data_age_minutes"],
                weather_source_state=result["weather_state"],
                is_scenario=is_scenario,
                scenario_run_id=scenario_run_id,
            )
            db.add(row)
            db.add(FeatureSnapshot(
                zone_id=zone.id,
                run_id=run_id,
                features={k: result["inputs"]["zone"][k] for k in result["inputs"]["zone"]},
                provenance={
                    "terrain": zone.terrain_source,
                    "landcover": zone.landcover_source,
                    "geology": zone.geology_source,
                    "weather": result["inputs"]["weather_source_id"],
                    "weather_state": result["weather_state"],
                },
            ))
            assessments.append(row)
            level_counts[result["hazard_level"]] += 1
            priority_counts[result["priority_level"]] += 1
            coverage_counts[result["coverage_level"]] = coverage_counts.get(result["coverage_level"], 0) + 1

            if not is_scenario:
                for seg in segments_by_zone.get(zone.id, []):
                    seg.model_risk_level = result["hazard_level"]
                    if seg.status_source == "MODEL_ESTIMATED":
                        if result["hazard_level"] in {RiskLevel.WARNING, RiskLevel.CRITICAL}:
                            seg.status = "AT_RISK"
                        elif seg.status == "AT_RISK":
                            seg.status = "OPEN"

    db.flush()

    if not is_scenario:
        from .alerts import generate_candidates  # local import to avoid a cycle

        new_alerts = generate_candidates(
            db, run_id=run_id, actor=actor, request_id=request_id, now=now
        )

    db.commit()

    summary = {
        "run_id": run_id,
        "mode": "SIMULATION" if is_scenario else "OPERATIONAL",
        "zones_assessed": len(assessments),
        "districts": [d.code for d in districts],
        "computed_at": iso(now),
        "model_version": P.MODEL_VERSION,
        "hazard_distribution": level_counts,
        "priority_distribution": priority_counts,
        "coverage_distribution": coverage_counts,
        "alert_candidates_created": len(new_alerts),
        "alert_candidates": new_alerts,
        "probability_status": "NOT_CALIBRATED",
    }
    if not is_scenario:
        bus.publish("risk.updated", summary)
        audit.record(db, actor=actor, action="risk.recalculated", entity="risk_run", entity_id=run_id,
                     reason=reason, payload={"zones": len(assessments), "districts": summary["districts"]},
                     request_id=request_id)
        db.commit()
    return summary


def district_risk_snapshot(db: Session, district_codes: list[str] | None) -> list[dict[str, Any]]:
    """Latest assessment per zone, joined with unit + district metadata (map payload)."""
    stmt = (
        select(SpatialUnit, District, RiskAssessment)
        .join(District, SpatialUnit.district_code == District.code)
        .join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
        .where(RiskAssessment.is_scenario.is_(False))
        .order_by(SpatialUnit.code, RiskAssessment.computed_at.desc())
    )
    if district_codes:
        stmt = stmt.where(SpatialUnit.district_code.in_(district_codes))
    latest: dict[int, tuple[SpatialUnit, District, RiskAssessment]] = {}
    for zone, district, assessment in db.execute(stmt):
        latest.setdefault(zone.id, (zone, district, assessment))
    return list(latest.values())


def threshold_crossing_minutes(
    db: Session, zone_id: int, level: RiskLevel, *, now: datetime | None = None
) -> int:
    """How long the unit has continuously been at/above a risk level."""
    now = now or datetime.now(timezone.utc)
    rows = list(db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.zone_id == zone_id, RiskAssessment.is_scenario.is_(False))
        .order_by(RiskAssessment.computed_at.desc())
        .limit(50)
    ).scalars())
    if not rows:
        return 0
    from ..domain import RISK_RANK

    rank = RISK_RANK[level]
    earliest = as_utc(rows[0].computed_at)
    for row in rows:
        if RISK_RANK.get(RiskLevel(row.hazard_level), 0) >= rank:
            earliest = as_utc(row.computed_at)
        else:
            break
    return minutes_since(earliest, now) or 0
