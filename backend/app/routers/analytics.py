"""Analytics and exports. Only traceable operational data is charted; model
performance is reported only when the validation gate allows it."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..models import (
    Alert,
    AlertDelivery,
    DataSource,
    District,
    LandslideIncident,
    ModelEvaluation,
    ModelVersion,
    Report,
    ResponseAssignment,
    RiskAssessment,
    SpatialUnit,
    WeatherObservation,
)
from ..services import audit, risk as risk_service
from ..services.serializers import source_dict, zone_summary
from ..services.util import as_utc, iso

router = APIRouter(prefix="/api/v1", tags=["analytics"])


def _scoped(db: Session, user: dict) -> tuple[list[str] | None, list[tuple]]:
    allowed = user_scopes(user)
    rows = risk_service.district_risk_snapshot(db, allowed)
    return allowed, rows


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), user=Depends(require("analytics:read")),
              district_code: str | None = None, days: int = Query(default=30, ge=1, le=365)):
    allowed, rows = _scoped(db, user)
    if district_code:
        if allowed is not None and district_code not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
        rows = [r for r in rows if r[0].district_code == district_code]
        allowed = [district_code]
    zone_ids = {z.id for z, _d, _a in rows}
    district_codes = sorted({z.district_code for z, _d, _a in rows})

    by_district: dict[str, dict] = {}
    for zone, district, assessment in rows:
        bucket = by_district.setdefault(district.code, {
            "district_code": district.code, "district_name": district.name, "state": district.state,
            "zones": 0, "hazard_sum": 0.0, "critical": 0, "warning": 0, "watch": 0, "safe": 0,
            "population_exposed": 0,
        })
        bucket["zones"] += 1
        bucket["hazard_sum"] += assessment.hazard_index
        bucket[assessment.hazard_level.lower()] += 1
        bucket["population_exposed"] += int(((assessment.inputs or {}).get("exposure") or {}).get("population_exposed") or 0)
    for bucket in by_district.values():
        bucket["avg_hazard"] = round(bucket["hazard_sum"] / max(1, bucket["zones"]), 2)
        bucket.pop("hazard_sum")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    observations = [
        o for o in db.execute(
            select(WeatherObservation).where(WeatherObservation.observed_at >= since)
            .order_by(WeatherObservation.observed_at)
        ).scalars()
        if o.district_code in district_codes
    ]
    rainfall_series = defaultdict(lambda: {"rainfall_24h": 0.0, "count": 0})
    for obs in observations:
        key = as_utc(obs.observed_at).date().isoformat()
        rainfall_series[key]["rainfall_24h"] += float(obs.rainfall_24h or 0.0)
        rainfall_series[key]["count"] += 1
    rainfall = [
        {"date": date, "rainfall_24h_mean": round(v["rainfall_24h"] / max(1, v["count"]), 2)}
        for date, v in sorted(rainfall_series.items())
    ]

    incidents = [i for i in db.execute(select(LandslideIncident)).scalars() if i.district_code in district_codes]
    incident_years = Counter(i.occurred_on.year for i in incidents)
    alerts = [a for a in db.execute(select(Alert).where(Alert.is_scenario.is_(False))).scalars()
              if a.zone_id in zone_ids]
    alert_status = Counter(a.status for a in alerts)
    alert_severity = Counter(a.severity for a in alerts)
    deliveries = list(db.execute(select(AlertDelivery)).scalars())
    delivery_status = Counter(d.status for d in deliveries if d.alert_id in {a.id for a in alerts})
    approved = [a for a in alerts if a.approved_at is not None]
    approval_lead_minutes = [
        int((as_utc(a.approved_at) - as_utc(a.created_at)).total_seconds() // 60) for a in approved
    ]

    assignments = [s for s in db.execute(select(ResponseAssignment)).scalars() if s.zone_id in zone_ids]
    response_minutes = [
        int((as_utc(s.closed_at) - as_utc(s.created_at)).total_seconds() // 60)
        for s in assignments if s.closed_at is not None
    ]
    reports = [r for r in db.execute(select(Report)).scalars() if r.district_code in district_codes]
    verified = [r for r in reports if r.status == "VERIFIED" and r.verified_at]
    verification_minutes = [
        int((as_utc(r.verified_at) - as_utc(r.created_at)).total_seconds() // 60) for r in verified
    ]

    sources = list(db.execute(select(DataSource)).scalars())
    latest_eval = db.execute(
        select(ModelEvaluation).order_by(ModelEvaluation.evaluated_at.desc()).limit(1)
    ).scalars().first()
    model = db.execute(select(ModelVersion).order_by(ModelVersion.released_at.desc()).limit(1)).scalars().first()

    return {
        "jurisdiction": {"districts": district_codes, "statewide": allowed is None},
        "generated_at": iso(datetime.now(timezone.utc)),
        "window_days": days,
        "risk": {
            "by_district": sorted(by_district.values(), key=lambda b: b["avg_hazard"], reverse=True),
            "by_level": dict(Counter(a.hazard_level for _z, _d, a in rows)),
            "by_priority": dict(Counter(a.priority_level for _z, _d, a in rows)),
            "by_coverage": dict(Counter(a.coverage_level for _z, _d, a in rows)),
            "thresholds": {"WATCH": 30, "WARNING": 60, "CRITICAL": 80},
            "probability_status": "NOT_CALIBRATED",
        },
        "rainfall": {"series": rainfall, "district_codes": district_codes,
                     "note": "District-centre model grid-point rainfall, not a gauge observation."},
        "incidents": {
            "by_year": [{"year": y, "count": c} for y, c in sorted(incident_years.items())],
            "total": len(incidents),
            "verified": sum(1 for i in incidents if i.verified),
            "synthetic": sum(1 for i in incidents if "SIMULATED" in (i.source or "")),
        },
        "alerts": {
            "by_status": dict(alert_status),
            "by_severity": dict(alert_severity),
            "delivery_status": dict(delivery_status),
            "approved": len(approved),
            "mean_approval_minutes": round(sum(approval_lead_minutes) / len(approval_lead_minutes), 1) if approval_lead_minutes else None,
        },
        "response": {
            "total": len(assignments),
            "by_status": dict(Counter(s.status for s in assignments)),
            "mean_close_minutes": round(sum(response_minutes) / len(response_minutes), 1) if response_minutes else None,
            "resolved": len(response_minutes),
        },
        "reports": {
            "total": len(reports),
            "pending": sum(1 for r in reports if r.status == "PENDING_VERIFICATION"),
            "verified": len(verified),
            "rejected": sum(1 for r in reports if r.status == "REJECTED"),
            "mean_verification_minutes": round(sum(verification_minutes) / len(verification_minutes), 1) if verification_minutes else None,
            "pii_note": "Aggregate counts only. Individual reports are restricted by role.",
        },
        "data_health": [source_dict(s) for s in sources],
        "model": {
            "version": model.version if model else None,
            "status": model.status if model else None,
            "validation_status": latest_eval.status if latest_eval else "VALIDATION IN PROGRESS",
            "metrics": (latest_eval.metrics if latest_eval and latest_eval.metrics else {}),
            "metrics_note": (
                "No measured metric is published because no verified inventory exists and the active "
                "model is not fitted. See the model card."
            ),
            "evaluated_at": iso(latest_eval.evaluated_at) if latest_eval else None,
        },
    }


@router.get("/analytics/export")
def export(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require("analytics:export")),
    dataset: str = Query(default="zones", pattern="^(zones|alerts|reports)$"),
    format: str = Query(default="csv", pattern="^(csv|geojson)$"),
):
    ctx = request_context(request)
    allowed, rows = _scoped(db, user)
    zones = {z.id: (z, d, a) for z, d, a in rows}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    provenance = {
        "generated_at": iso(datetime.now(timezone.utc)),
        "model_version": "suscept-v0.1+trigger-v0.1",
        "probability_status": "NOT_CALIBRATED",
        "exported_by": user["email"],
        "disclaimer": "Decision support only. Hazard is an uncalibrated index, not a probability.",
    }

    if dataset == "zones":
        features = []
        for zone, district, assessment in rows:
            props = {k: v for k, v in zone_summary(zone, district, assessment).items() if k != "geometry"}
            features.append({"type": "Feature", "geometry": zone.geometry, "properties": props})
        if format == "geojson":
            payload = json.dumps({"type": "FeatureCollection", "features": features, "provenance": provenance}, indent=2)
            audit.record(db, actor=user, action="analytics.export", entity="export", entity_id=f"zones:{stamp}",
                         reason="GeoJSON export", payload={"rows": len(features)}, request_id=ctx["request_id"])
            db.commit()
            return StreamingResponse(io.BytesIO(payload.encode()), media_type="application/geo+json",
                                     headers={"Content-Disposition": f'attachment; filename="bhushakti-zones-{stamp}.geojson"'})
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["zone_code", "zone_name", "district", "state", "hazard_index", "hazard_level",
                         "probability_status", "exposure_score", "vulnerability_score", "priority_score",
                         "priority_level", "coverage_level", "weather_source_state", "computed_at",
                         "model_version", "disclaimer"])
        for zone, district, assessment in rows:
            writer.writerow([zone.code, zone.name, district.name, district.state, assessment.hazard_index,
                             assessment.hazard_level, "NOT_CALIBRATED", assessment.exposure_score,
                             assessment.vulnerability_score, assessment.priority_score,
                             assessment.priority_level, assessment.coverage_level,
                             assessment.weather_source_state, iso(assessment.computed_at),
                             assessment.model_version, provenance["disclaimer"]])
        audit.record(db, actor=user, action="analytics.export", entity="export", entity_id=f"zones:{stamp}",
                     reason="CSV export", payload={"rows": len(rows)}, request_id=ctx["request_id"])
        db.commit()
        return StreamingResponse(io.BytesIO(buffer.getvalue().encode()), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="bhushakti-zones-{stamp}.csv"'})

    if dataset == "alerts":
        alerts = [a for a in db.execute(select(Alert).where(Alert.is_scenario.is_(False))).scalars()
                  if a.zone_id in zones]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["reference", "zone", "district", "severity", "status", "hazard_index",
                         "priority_level", "created_at", "approved_at", "expires", "language",
                         "template_version", "policy_version", "reason"])
        for alert in alerts:
            zone, district, _assessment = zones[alert.zone_id]
            writer.writerow([alert.reference, zone.name, district.name, alert.severity, alert.status,
                             alert.hazard_index, alert.priority_level, iso(alert.created_at),
                             iso(alert.approved_at), iso(alert.expires), alert.language,
                             alert.template_version, alert.policy_version, alert.reason])
        audit.record(db, actor=user, action="analytics.export", entity="export", entity_id=f"alerts:{stamp}",
                     reason="CSV export", payload={"rows": len(alerts)}, request_id=ctx["request_id"])
        db.commit()
        return StreamingResponse(io.BytesIO(buffer.getvalue().encode()), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="bhushakti-alerts-{stamp}.csv"'})

    if user["role"] == "researcher":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Report-level export is restricted for researchers")
    reports = [r for r in db.execute(select(Report)).scalars()
               if r.district_code in {d.code for _z, d, _a in rows}]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["report_id", "client_uuid", "district", "zone_id", "hazard_type", "status",
                     "observed_at", "created_at", "verified_at", "sync_source", "media_count",
                     "risk_adjustment_applied"])
    for report in reports:
        writer.writerow([report.id, report.client_uuid, report.district_code, report.zone_id,
                         report.hazard_type, report.status, iso(report.observed_at), iso(report.created_at),
                         iso(report.verified_at), report.sync_source, len(report.media),
                         report.risk_adjustment_applied])
    audit.record(db, actor=user, action="analytics.export", entity="export", entity_id=f"reports:{stamp}",
                 reason="CSV export (no personal data)", payload={"rows": len(reports)},
                 request_id=ctx["request_id"])
    db.commit()
    return StreamingResponse(io.BytesIO(buffer.getvalue().encode()), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="bhushakti-reports-{stamp}.csv"'})
