"""Alert review and approval workflow. Only approved alerts are ever served publicly."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..domain import ALERT_DISCLAIMER
from ..deps import request_context, require, user_scopes
from ..models import Alert, AlertDelivery, District, RiskAssessment, SpatialUnit
from ..services import alerts as alert_service, audit
from ..services.events import bus
from ..services.serializers import alert_dict
from ..services.util import page_bounds

router = APIRouter(prefix="/api/v1", tags=["alerts"])


class ApproveRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=1000)
    languages: list[str] = Field(default_factory=lambda: ["en"], max_length=5)


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=1000)
    all_clear: bool = False


class ManualCandidateRequest(BaseModel):
    zone_id: int
    reason: str = Field(min_length=15, max_length=1000)
    instructions: str = Field(default="", max_length=2000)


def _alert_context(db: Session, alert_id: int, user: dict) -> tuple[Alert, SpatialUnit, District]:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    zone = db.get(SpatialUnit, alert.zone_id)
    district = db.get(District, zone.district_code) if zone else None
    if zone is None or district is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Alert geometry is missing")
    allowed = user_scopes(user)
    if allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    return alert, zone, district


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    user=Depends(require("alerts:read")),
    status_filter: str | None = None,
    district_code: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    allowed = user_scopes(user)
    stmt = select(Alert).where(Alert.is_scenario.is_(False))
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter.upper())
    if severity:
        stmt = stmt.where(Alert.severity == severity.upper())
    rows = list(db.execute(stmt.order_by(Alert.created_at.desc())).scalars())
    zones = {z.id: z for z in db.execute(select(SpatialUnit)).scalars()}
    districts = {d.code: d for d in db.execute(select(District)).scalars()}
    filtered = []
    for alert in rows:
        zone = zones.get(alert.zone_id)
        if zone is None:
            continue
        if allowed is not None and zone.district_code not in allowed:
            continue
        if district_code and zone.district_code != district_code:
            continue
        filtered.append((alert, zone, districts.get(zone.district_code)))
    deliveries_by_alert: dict[int, list[AlertDelivery]] = {}
    for delivery in db.execute(select(AlertDelivery)).scalars():
        deliveries_by_alert.setdefault(delivery.alert_id, []).append(delivery)
    total = len(filtered)
    page = filtered[offset:offset + limit]
    return {
        "alerts": [alert_dict(a, z, d, deliveries_by_alert.get(a.id, [])) for a, z, d in page],
        "meta": page_bounds(total, limit, offset),
        "policy": {
            "approval_required": True,
            "note": "Candidates are never published automatically. Approval is recorded with actor and reason.",
        },
        "demo_mode": settings.demo_mode,
    }


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db), user=Depends(require("alerts:read"))):
    alert, zone, district = _alert_context(db, alert_id, user)
    deliveries = list(db.execute(select(AlertDelivery).where(AlertDelivery.alert_id == alert.id)).scalars())
    return alert_dict(alert, zone, district, deliveries)


@router.get("/alerts/{alert_id}/cap")
def get_cap(alert_id: int, db: Session = Depends(get_db), user=Depends(require("alerts:read"))):
    alert, zone, district = _alert_context(db, alert_id, user)
    return alert_service.cap_message(alert, zone, district)


@router.post("/alerts/manual-candidate", status_code=status.HTTP_201_CREATED)
def manual_candidate(payload: ManualCandidateRequest, request: Request, db: Session = Depends(get_db),
                     user=Depends(require("alerts:prepare"))):
    """Authority-initiated candidate (for example after a field phone call).

    It is still only a CANDIDATE: a separate approver must publish it, and the
    hazard context shown is the current assessment, unchanged.
    """
    ctx = request_context(request)
    zone = db.get(SpatialUnit, payload.zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    allowed = user_scopes(user)
    if allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    active = db.execute(
        select(Alert).where(Alert.zone_id == zone.id,
                            Alert.status.in_(["CANDIDATE", "APPROVED", "DELIVERED"]))
    ).scalars().first()
    if active is not None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"An active alert already exists for this unit ({active.reference})")
    assessment = db.execute(
        select(RiskAssessment).where(RiskAssessment.zone_id == zone.id,
                                     RiskAssessment.is_scenario.is_(False))
        .order_by(RiskAssessment.computed_at.desc()).limit(1)
    ).scalars().first()
    if assessment is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No assessment exists for this unit yet")
    policy = alert_service.active_policy(db)
    severity = alert_service.severity_for(policy, assessment.hazard_index)
    alert = Alert(
        reference=alert_service.new_reference(db), zone_id=zone.id, severity=severity.value,
        status="CANDIDATE",
        headline=f"{severity.value} landslide hazard — {zone.name}, manual authority candidate",
        reason=(
            f"Authority-initiated candidate. {payload.reason} Current model hazard index "
            f"{assessment.hazard_index:.0f}/100 (uncalibrated prototype index)."
        ),
        instructions=payload.instructions or alert_service.INSTRUCTIONS["en"].get(severity.value, ""),
        onset=datetime.now(timezone.utc), expires=datetime.now(timezone.utc) + timedelta(hours=6),
        geometry=zone.geometry,
        threatened_assets=[],
        source="Authority-initiated candidate (manual review) — requires approval",
        disclaimer=ALERT_DISCLAIMER,
        template_version=alert_service.TEMPLATE_VERSION, language="en",
        hazard_index=assessment.hazard_index, priority_level=assessment.priority_level,
        policy_version=policy.version, is_scenario=False, created_by=user["id"],
    )
    db.add(alert)
    db.flush()
    db.add(alert_service.AlertApproval(alert_id=alert.id, actor_id=user["id"], action="CREATED",
                                       reason=payload.reason, at=datetime.now(timezone.utc)))
    audit.record(db, actor=user, action="alert.manual_candidate", entity="alert", entity_id=alert.id,
                 reason=payload.reason, payload={"zone_id": zone.id, "hazard_index": assessment.hazard_index},
                 request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    bus.publish("alert.created", {"id": alert.id, "reference": alert.reference, "severity": alert.severity})
    return alert_dict(alert, zone, db.get(District, zone.district_code))


@router.post("/alerts/generate")
def generate(request: Request, db: Session = Depends(get_db),
             user=Depends(require("alerts:prepare"))):
    ctx = request_context(request)
    latest = db.execute(
        select(RiskAssessment).where(RiskAssessment.is_scenario.is_(False))
        .order_by(RiskAssessment.computed_at.desc()).limit(1)
    ).scalars().first()
    if latest is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No assessment exists yet; run a recalculation first")
    created = alert_service.generate_candidates(
        db, run_id=latest.run_id, actor=user, request_id=ctx["request_id"],
    )
    db.commit()
    audit.record(db, actor=user, action="alerts.generated", entity="alert_batch",
                 entity_id=latest.run_id, reason="Manual candidate generation from the latest run",
                 payload={"created": len(created)}, request_id=ctx["request_id"])
    db.commit()
    return {"run_id": latest.run_id, "candidates_created": len(created), "candidates": created}


@router.post("/alerts/{alert_id}/approve")
def approve(alert_id: int, payload: ApproveRequest, request: Request, db: Session = Depends(get_db),
            user=Depends(require("alerts:approve"))):
    ctx = request_context(request)
    alert, _zone, _district = _alert_context(db, alert_id, user)
    try:
        result = alert_service.approve(
            db, alert, actor=user, reason=payload.reason, languages=payload.languages,
            request_id=ctx["request_id"],
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return result


@router.post("/alerts/{alert_id}/reject")
def reject(alert_id: int, payload: ReasonRequest, request: Request, db: Session = Depends(get_db),
           user=Depends(require("alerts:approve"))):
    ctx = request_context(request)
    alert, _zone, _district = _alert_context(db, alert_id, user)
    try:
        alert_service.reject(db, alert, actor=user, reason=payload.reason, request_id=ctx["request_id"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"id": alert.id, "status": alert.status, "rejected_at": alert_dict(alert)["rejected_at"]}


@router.post("/alerts/{alert_id}/cancel")
def cancel(alert_id: int, payload: ReasonRequest, request: Request, db: Session = Depends(get_db),
           user=Depends(require("alerts:cancel"))):
    ctx = request_context(request)
    alert, _zone, _district = _alert_context(db, alert_id, user)
    try:
        alert_service.cancel(db, alert, actor=user, reason=payload.reason, all_clear=payload.all_clear,
                             request_id=ctx["request_id"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"id": alert.id, "status": alert.status, "at": datetime.now(timezone.utc).isoformat()}
