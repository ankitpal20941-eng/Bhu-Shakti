"""Risk map, zone intelligence, trajectory and recalculation endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..domain import PRIORITY_LABELS, RISK_THRESHOLDS, SAFETY_DISCLAIMER, RiskLevel
from ..engine import params as P
from ..engine.trajectory import build_trajectory
from ..models import (
    Alert,
    District,
    LandslideIncident,
    Report,
    RiskAssessment,
    RoadSegment,
    SpatialUnit,
    WeatherObservation,
)
from ..services import risk as risk_service
from ..services.events import bus
from ..services.serializers import (
    alert_dict,
    district_dict,
    report_dict,
    segment_dict,
    zone_detail,
    zone_summary,
)
from ..services.util import as_utc, iso, page_bounds

router = APIRouter(prefix="/api/v1", tags=["risk"])


class RecalculateRequest(BaseModel):
    district_codes: list[str] | None = None
    reason: str = Field(default="Manual recalculation requested by authority", min_length=4, max_length=400)


def _scope_codes(user: dict[str, Any]) -> list[str] | None:
    return user_scopes(user)


def _zone_context(db: Session, zone_id: int, user: dict[str, Any]) -> tuple[SpatialUnit, District, RiskAssessment | None]:
    zone = db.get(SpatialUnit, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk unit not found")
    allowed = _scope_codes(user)
    if allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    district = db.get(District, zone.district_code)
    if district is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "District metadata missing")
    assessment = risk_service.latest_assessment(db, zone.id)
    return zone, district, assessment


@router.get("/risk-zones")
def risk_zones(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require("risk:read")),
    district_code: str | None = None,
    state: str | None = None,
    risk_level: str | None = None,
    priority_level: str | None = None,
    min_hazard: float | None = Query(default=None, ge=0, le=100),
    max_hazard: float | None = Query(default=None, ge=0, le=100),
    lat_min: float | None = None,
    lat_max: float | None = None,
    lon_min: float | None = None,
    lon_max: float | None = None,
    q: str | None = None,
    limit: int = Query(default=1000, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):
    allowed = _scope_codes(user)
    rows = risk_service.district_risk_snapshot(db, allowed)
    features: list[dict[str, Any]] = []
    for zone, district, assessment in rows:
        if district_code and zone.district_code != district_code:
            continue
        if state and district.state.lower() != state.lower():
            continue
        if risk_level and assessment.hazard_level != risk_level.upper():
            continue
        if priority_level and assessment.priority_level != priority_level.upper():
            continue
        if min_hazard is not None and assessment.hazard_index < min_hazard:
            continue
        if max_hazard is not None and assessment.hazard_index > max_hazard:
            continue
        if lat_min is not None and zone.centroid_lat < lat_min:
            continue
        if lat_max is not None and zone.centroid_lat > lat_max:
            continue
        if lon_min is not None and zone.centroid_lon < lon_min:
            continue
        if lon_max is not None and zone.centroid_lon > lon_max:
            continue
        if q:
            needle = q.lower()
            if needle not in zone.name.lower() and needle not in zone.code.lower() and needle not in district.name.lower():
                continue
        properties = zone_summary(zone, district, assessment)
        properties.pop("geometry", None)
        features.append({"type": "Feature", "geometry": zone.geometry, "properties": properties})

    features.sort(key=lambda f: (f["properties"].get("hazard_index") or 0), reverse=True)
    total = len(features)
    page = features[offset:offset + limit]
    return {
        "type": "FeatureCollection",
        "features": page,
        "meta": {
            **page_bounds(total, limit, offset),
            "thresholds": RISK_THRESHOLDS,
            "probability_status": "NOT_CALIBRATED",
            "disclaimer": SAFETY_DISCLAIMER,
            "scope": "statewide" if allowed is None else allowed,
            "generated_at": iso(__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
        },
    }


@router.get("/risk-zones/{zone_id}")
def risk_zone_detail(zone_id: int, db: Session = Depends(get_db), user=Depends(require("risk:read"))):
    zone, district, assessment = _zone_context(db, zone_id, user)

    incidents = []
    for incident in db.execute(
        select(LandslideIncident).where(LandslideIncident.district_code == zone.district_code)
    ).scalars():
        from ..engine.exposure import haversine_km

        distance = haversine_km(zone.centroid_lat, zone.centroid_lon, incident.lat, incident.lon)
        if distance <= 8:
            incidents.append({
                "id": incident.id,
                "occurred_on": incident.occurred_on.isoformat(),
                "date_uncertainty_days": incident.date_uncertainty_days,
                "distance_km": round(distance, 2),
                "location_accuracy_m": incident.location_accuracy_m,
                "verified": incident.verified,
                "source": incident.source,
                "description": incident.description,
            })
    incidents.sort(key=lambda i: i["occurred_on"], reverse=True)

    report_rows = list(db.execute(
        select(Report).where(Report.zone_id == zone.id).order_by(Report.created_at.desc()).limit(25)
    ).scalars())
    if user["role"] == "researcher":
        report_rows = [r for r in report_rows if r.status == "VERIFIED"]

    segments = list(db.execute(select(RoadSegment).where(RoadSegment.zone_id == zone.id)).scalars())
    history = [
        {
            "computed_at": iso(row.computed_at),
            "hazard_index": row.hazard_index,
            "hazard_level": row.hazard_level,
            "priority_level": row.priority_level,
            "coverage_level": row.coverage_level,
        }
        for row in db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.zone_id == zone.id, RiskAssessment.is_scenario.is_(False))
            .order_by(RiskAssessment.computed_at.desc()).limit(48)
        ).scalars()
    ]
    history.reverse()

    trajectory = None
    if assessment:
        inputs = assessment.inputs or {}
        rain = inputs.get("rainfall") or {}
        forecasts = {int(k): v for k, v in (inputs.get("forecasts") or {}).items()}
        trajectory = build_trajectory(
            static_index=(inputs.get("static") or {}).get("index", 0.0),
            rainfall_1h=rain.get("1h"), rainfall_6h=rain.get("6h"),
            rainfall_24h=rain.get("24h"), rainfall_72h=rain.get("72h"),
            soil_moisture_pct=inputs.get("soil_moisture_pct"),
            month=as_utc(assessment.computed_at).month if assessment else 1,
            forecasts=forecasts,
            forecast_issued_at=inputs.get("forecast_issued_at"),
        )
        trajectory["forecast_observations"] = [
            {"horizon_h": k, "rainfall_mm": v} for k, v in sorted(forecasts.items())
        ]

    open_alerts = list(db.execute(
        select(Alert).where(
            Alert.zone_id == zone.id,
            Alert.status.in_(["CANDIDATE", "APPROVED", "DELIVERED"]),
        ).order_by(Alert.created_at.desc())
    ).scalars())

    detail = zone_detail(
        zone, district, assessment,
        incidents=incidents,
        reports=report_rows,
        segments=segments,
        trajectory=trajectory,
        history=history,
    )
    detail["district"] = district_dict(district)
    detail["open_alerts"] = [alert_dict(a, zone, district) for a in open_alerts]
    detail["thresholds"] = RISK_THRESHOLDS
    detail["priority_labels"] = {k: v for k, v in PRIORITY_LABELS.items()}
    return detail


@router.get("/risk-zones/{zone_id}/explanation")
def risk_explanation(zone_id: int, db: Session = Depends(get_db), user=Depends(require("risk:read"))):
    zone, district, assessment = _zone_context(db, zone_id, user)
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No assessment exists for this unit yet")
    inputs = assessment.inputs or {}
    return {
        "zone": {"id": zone.id, "code": zone.code, "name": zone.name, "district": district.name},
        "hazard_index": assessment.hazard_index,
        "hazard_level": assessment.hazard_level,
        "probability_status": "NOT_CALIBRATED",
        "hazard_probability": None,
        "model_version": assessment.model_version,
        "drivers": assessment.drivers,
        "components": inputs.get("components"),
        "static_terms": (inputs.get("static") or {}).get("terms"),
        "intercept": (inputs.get("static") or {}).get("intercept"),
        "trigger": inputs.get("trigger"),
        "field_evidence": inputs.get("field_evidence"),
        "coverage": inputs.get("coverage"),
        "model_parameters": P.PARAMS.documentation(),
        "method_note": (
            "Susceptibility is a logistic index with exact additive log-odds attribution. It is not "
            "trained or calibrated on a verified inventory, so no SHAP explanation or probability is claimed."
        ),
    }


@router.get("/risk/trajectory")
def risk_trajectory(zone_id: int, db: Session = Depends(get_db), user=Depends(require("risk:read"))):
    zone, district, assessment = _zone_context(db, zone_id, user)
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No assessment exists for this unit yet")
    inputs = assessment.inputs or {}
    rain = inputs.get("rainfall") or {}
    forecasts = {int(k): v for k, v in (inputs.get("forecasts") or {}).items()}
    trajectory = build_trajectory(
        static_index=(inputs.get("static") or {}).get("index", 0.0),
        rainfall_1h=rain.get("1h"), rainfall_6h=rain.get("6h"),
        rainfall_24h=rain.get("24h"), rainfall_72h=rain.get("72h"),
        soil_moisture_pct=inputs.get("soil_moisture_pct"),
        month=as_utc(assessment.computed_at).month,
        forecasts=forecasts,
        forecast_issued_at=inputs.get("forecast_issued_at"),
    )
    return {
        "zone_id": zone.id,
        "zone_name": zone.name,
        "current": {"hazard_index": assessment.hazard_index, "hazard_level": assessment.hazard_level},
        **trajectory,
        "disclaimer": "Forecast horizons are shown only where forecast rainfall exists. No values are invented.",
    }


@router.get("/risk/summary")
def risk_summary(
    db: Session = Depends(get_db),
    user=Depends(require("risk:read")),
    district_code: str | None = None,
):
    allowed = _scope_codes(user)
    if district_code:
        if allowed is not None and district_code not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
        allowed = [district_code]

    rows = risk_service.district_risk_snapshot(db, allowed)
    hazard_counts = {level.value: 0 for level in RiskLevel}
    coverage_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    population = 0
    population_known = False
    last_run = None
    for zone, district, assessment in rows:
        hazard_counts[assessment.hazard_level] = hazard_counts.get(assessment.hazard_level, 0) + 1
        coverage_counts[assessment.coverage_level] = coverage_counts.get(assessment.coverage_level, 0) + 1
        if assessment.hazard_level in {"WARNING", "CRITICAL"}:
            exposure = (assessment.inputs or {}).get("exposure") or {}
            if exposure.get("population_exposed"):
                population_known = True
                population += int(exposure["population_exposed"])
        if last_run is None or as_utc(assessment.computed_at) > last_run:
            last_run = as_utc(assessment.computed_at)

    district_codes = sorted({z.district_code for z, _d, _a in rows})
    alert_rows = list(db.execute(
        select(Alert).where(Alert.is_scenario.is_(False))
    ).scalars())
    active_alerts = sum(1 for a in alert_rows if a.status in {"APPROVED", "DELIVERED"})
    pending_alerts = sum(1 for a in alert_rows if a.status == "CANDIDATE")
    zone_ids = {z.id for z, _d, _a in rows}
    segments = list(db.execute(select(RoadSegment)).scalars())
    roads_at_risk = sum(1 for s in segments if s.zone_id in zone_ids and s.status in {"AT_RISK", "RESTRICTED"})
    roads_blocked = sum(1 for s in segments if s.zone_id in zone_ids and s.status == "BLOCKED")
    pending_reports = len([
        r for r in db.execute(select(Report).where(Report.status == "PENDING_VERIFICATION")).scalars()
        if r.district_code in district_codes or r.district_code is None
    ])

    conditions = []
    for code in district_codes:
        district = db.get(District, code)
        weather = db.execute(
            select(WeatherObservation).where(WeatherObservation.district_code == code)
            .order_by(WeatherObservation.observed_at.desc()).limit(1)
        ).scalars().first()
        from ..models import DataSource

        source = db.get(DataSource, weather.source_id) if weather else None
        state = risk_service.effective_weather_state(source, as_utc(weather.observed_at) if weather else None,
                                                    __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        conditions.append({
            "district_code": code,
            "district_name": district.name if district else code,
            "state": district.state if district else None,
            "rainfall_1h": weather.rainfall_1h if weather else None,
            "rainfall_24h": weather.rainfall_24h if weather else None,
            "rainfall_72h": weather.rainfall_72h if weather else None,
            "soil_moisture_pct": weather.soil_moisture_pct if weather else None,
            "observed_at": iso(weather.observed_at) if weather else None,
            "source_id": weather.source_id if weather else None,
            "source_state": state.value,
            "attribution": source.attribution if source else None,
        })

    return {
        "jurisdiction": {"districts": district_codes, "statewide": allowed is None},
        "kpis": {
            "zones": len(rows),
            "critical_zones": hazard_counts.get("CRITICAL", 0),
            "warning_zones": hazard_counts.get("WARNING", 0),
            "watch_zones": hazard_counts.get("WATCH", 0),
            "safe_zones": hazard_counts.get("SAFE", 0),
            "active_alerts": active_alerts,
            "pending_alerts": pending_alerts,
            "roads_at_risk": roads_at_risk,
            "roads_blocked": roads_blocked,
            "pending_reports": pending_reports,
            "population_exposed_estimate": population if population_known else None,
        },
        "population_note": "Population exposure is a dataset estimate from demo assets, not a census of people at risk.",
        "hazard_distribution": hazard_counts,
        "coverage_distribution": coverage_counts,
        "thresholds": RISK_THRESHOLDS,
        "probability_status": "NOT_CALIBRATED",
        "last_run": iso(last_run),
        "conditions": conditions,
        "disclaimer": SAFETY_DISCLAIMER,
        "demo_mode": settings.demo_mode,
    }


@router.post("/risk/recalculate")
def recalculate(payload: RecalculateRequest, request: Request, db: Session = Depends(get_db),
                user=Depends(require("risk:recalculate"))):
    ctx = request_context(request)
    allowed = _scope_codes(user)
    targets = payload.district_codes
    if allowed is not None:
        if targets:
            outside = [c for c in targets if c not in allowed]
            if outside:
                raise HTTPException(status.HTTP_403_FORBIDDEN, f"Outside your scope: {outside}")
        else:
            targets = allowed
    summary = risk_service.recalculate(
        db, district_codes=targets, actor=user, request_id=ctx["request_id"], reason=payload.reason
    )
    bus.publish("risk.updated", {"run_id": summary.get("run_id"), "zones": summary.get("zones_assessed")})
    return summary
