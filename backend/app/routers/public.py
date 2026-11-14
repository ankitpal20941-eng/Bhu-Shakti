"""Public citizen endpoints: plain-language local risk, official advisories and
anonymous hazard reporting. No model internals, SHAP values or probabilities."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..engine.exposure import haversine_km
from ..models import Alert, DataSource, District, FeatureFlag, InfrastructureAsset, RiskAssessment, SpatialUnit
from ..security import rate_limiter
from ..services import reports as report_service
from ..services.alerts import INSTRUCTIONS, LANGUAGES
from ..services.reports import ReportError
from ..services.risk import effective_weather_state, latest_assessment, latest_weather
from ..services.serializers import report_dict
from ..services.util import as_utc, iso

router = APIRouter(prefix="/api/v1/public", tags=["public"])

SEVERITY_ORDER = {"CRITICAL": 3, "WARNING": 2, "WATCH": 1, "SAFE": 0}


def _flags(db: Session) -> dict[str, bool]:
    return {f.key: f.enabled for f in db.execute(select(FeatureFlag)).scalars()}


@router.get("/config")
def public_config(db: Session = Depends(get_db)):
    flags = _flags(db)
    return {
        "app_name": "BHUSHAKTI AI",
        "mode": "DEMO" if settings.demo_mode else "PRODUCTION",
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "disclaimer": (
            "BHUSHAKTI AI provides decision support for authorities. Hazard scores are prototype, "
            "uncalibrated model outputs — not official warnings or predictions of a specific landslide. "
            "Always follow the National Disaster Management Authority and your district administration."
        ),
        "languages": LANGUAGES,
        "reviewed_languages": ["en"],
        "features": {
            "public_alerts": flags.get("public_citizen_alerts", False),
            "citizen_reporting": True,
            "scenario_lab": flags.get("scenario_lab", False),
            "image_ai": flags.get("image_ai", False),
            "sms_delivery": flags.get("sms_delivery", False),
        },
        "districts": [
            {"code": d.code, "name": d.name, "state": d.state, "lat": d.lat, "lon": d.lon,
             "boundary_note": d.boundary_note}
            for d in db.execute(select(District)).scalars()
        ],
        "data_attribution": [
            {"source": s.name, "provider": s.provider, "attribution": s.attribution, "state": s.state}
            for s in db.execute(select(DataSource)).scalars()
            if s.state in {"LIVE", "SIMULATED", "DEGRADED", "STALE"}
        ],
    }


def _nearest_zone(db: Session, lat: float, lon: float) -> tuple[SpatialUnit | None, float | None]:
    best: tuple[float, SpatialUnit] | None = None
    for zone in db.execute(select(SpatialUnit)).scalars():
        distance = haversine_km(lat, lon, zone.centroid_lat, zone.centroid_lon)
        if best is None or distance < best[0]:
            best = (distance, zone)
    if best is None or best[0] > 25:
        return None, None
    return best[1], best[0]


@router.get("/risk")
def public_risk(lat: float, lon: float, lang: str = "en", db: Session = Depends(get_db)):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Coordinates out of range")
    lang = lang if lang in LANGUAGES else "en"
    zone, distance = _nearest_zone(db, lat, lon)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No pilot risk unit covers this location yet (three districts are live).")
    district = db.get(District, zone.district_code)
    assessment = latest_assessment(db, zone.id)
    if assessment is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No current assessment for this area")

    level = assessment.hazard_level
    inputs = assessment.inputs or {}
    rain = inputs.get("rainfall") or {}
    weather = latest_weather(db, zone.district_code)
    source = db.get(DataSource, weather.source_id) if weather else None
    state = effective_weather_state(source, as_utc(weather.observed_at) if weather else None,
                                   datetime.now(timezone.utc))

    alerts = list(db.execute(
        select(Alert).where(
            Alert.zone_id == zone.id,
            Alert.status.in_(["APPROVED", "DELIVERED", "ALL_CLEAR"]),
        ).order_by(Alert.created_at.desc()).limit(3)
    ).scalars())
    official = [a for a in alerts if a.status in {"APPROVED", "DELIVERED"}]

    hospital = None
    best_distance = None
    for asset in db.execute(select(InfrastructureAsset).where(
            InfrastructureAsset.district_code == zone.district_code,
            InfrastructureAsset.kind == "hospital")).scalars():
        d = haversine_km(lat, lon, asset.lat, asset.lon)
        if best_distance is None or d < best_distance:
            best_distance, hospital = d, asset

    slope = zone.slope_deg or 0
    if slope >= 30:
        terrain_phrase = "The ground here is on a steep slope."
    elif slope >= 15:
        terrain_phrase = "The ground here is on a moderate slope."
    else:
        terrain_phrase = "The ground here is relatively gentle."
    rain_24 = rain.get("24h")
    reasons = [terrain_phrase]
    if rain_24 is not None:
        if rain_24 >= 50:
            reasons.append(f"About {rain_24:.0f} mm of rain fell in the last 24 hours, which is a lot for this area.")
        elif rain_24 >= 10:
            reasons.append(f"About {rain_24:.0f} mm of rain fell in the last 24 hours.")
        else:
            reasons.append("Little rain has been recorded in the last 24 hours.")
    if (inputs.get("field_evidence") or {}).get("applied_points"):
        reasons.append("An officer has verified slope damage nearby.")

    return {
        "location": {"lat": lat, "lon": lon, "nearest_unit": zone.name, "distance_km": round(distance or 0, 1),
                      "district": district.name if district else None, "state": district.state if district else None},
        "risk_level": level,
        "risk_label": {
            "CRITICAL": "Very high risk right now",
            "WARNING": "High risk right now",
            "WATCH": "Some risk — stay alert",
            "SAFE": "No elevated risk indicated",
        }[level],
        "plain_reason": " ".join(reasons),
        "updated_at": iso(assessment.computed_at),
        "observation_time": iso(weather.observed_at) if weather else None,
        "data_state": state.value,
        "official_advisory": {
            "active": bool(official),
            "count": len(official),
            "latest": {
                "reference": official[0].reference,
                "headline": official[0].headline,
                "approved_at": iso(official[0].approved_at),
                "expires": iso(official[0].expires),
                "instructions": official[0].instructions,
            } if official else None,
            "note": "Only authority-approved advisories are shown here. Model output alone never creates an advisory.",
        },
        "safety_instructions": INSTRUCTIONS[lang].get(level, INSTRUCTIONS[lang]["WATCH"]),
        "language": lang,
        "language_reviewed": lang == "en",
        "nearest_hospital": {
            "name": hospital.name, "distance_km": round(best_distance, 1),
            "note": "Reference location from the demo exposure dataset; verify locally.",
        } if hospital else None,
        "disclaimer": (
            "This is decision support, not an official warning, and it does not predict a specific landslide. "
            "In an emergency call 112 / your district control room."
        ),
        "can_report": True,
    }


@router.get("/alerts")
def public_alerts(db: Session = Depends(get_db), district_code: str | None = None):
    if not _flags(db).get("public_citizen_alerts", False):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Public advisories are disabled")
    zones = {z.id: z for z in db.execute(select(SpatialUnit)).scalars()}
    districts = {d.code: d for d in db.execute(select(District)).scalars()}
    rows = list(db.execute(
        select(Alert).where(
            Alert.status.in_(["APPROVED", "DELIVERED", "ALL_CLEAR"]),
            Alert.is_scenario.is_(False),
        ).order_by(Alert.created_at.desc()).limit(50)
    ).scalars())
    out = []
    for alert in rows:
        zone = zones.get(alert.zone_id)
        if zone is None:
            continue
        if district_code and zone.district_code != district_code:
            continue
        out.append({
            "reference": alert.reference,
            "severity": alert.severity,
            "status": alert.status,
            "headline": alert.headline,
            "instructions": alert.instructions,
            "area": zone.name,
            "district": districts[zone.district_code].name if zone.district_code in districts else None,
            "onset": iso(alert.onset),
            "expires": iso(alert.expires),
            "approved_at": iso(alert.approved_at),
            "language": alert.language,
            "disclaimer": alert.disclaimer,
        })
    return {
        "alerts": out,
        "count": len(out),
        "note": "Approved advisories only. Pending candidates are never shown publicly.",
    }


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def citizen_report(
    request: Request,
    db: Session = Depends(get_db),
    hazard_type: str = Form(...),
    description: str = Form(""),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    gps_accuracy_m: float | None = Form(None),
    observed_at: str | None = Form(None),
    consent: bool = Form(False),
    client_uuid: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    rate_limiter.check(f"public-report:{client_ip}", 5, 60)
    if not consent:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Consent is required before submitting location or media")
    if hazard_type.upper() not in {"GROUND_CRACK", "SLOPE_MOVEMENT", "ROCKFALL", "ROAD_BLOCKAGE",
                                   "DEBRIS_FLOW", "SUBSIDENCE", "OTHER"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown hazard type")
    uploads = [f for f in files if f and f.filename] if files else []
    try:
        report, duplicate = report_service.create_report(
            db,
            payload={
                "hazard_type": hazard_type, "description": description, "lat": lat, "lon": lon,
                "gps_accuracy_m": gps_accuracy_m, "observed_at": observed_at, "consent": consent,
                "client_uuid": client_uuid, "anonymous": True,
            },
            uploads=uploads, actor=None, sync_source="citizen_public",
            request_id="public",
        )
    except ReportError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return {
        "report": report_dict(report),
        "duplicate": duplicate,
        "status_explanation": (
            "Your report is PENDING VERIFICATION. It will not be published or change any warning until "
            "an authorised officer verifies it."
        ),
    }
