"""Field/citizen reports: submission, media upload, verification and offline sync."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..models import Report, SpatialUnit
from ..security import rate_limiter
from ..services import audit, reports as report_service
from ..services.reports import ReportError
from ..services.serializers import report_dict
from ..services.util import iso, page_bounds

router = APIRouter(prefix="/api/v1", tags=["reports"])


class VerifyRequest(BaseModel):
    decision: str = Field(pattern="^(VERIFIED|REJECTED)$")
    note: str = Field(min_length=4, max_length=2000)


class SyncRequest(BaseModel):
    items: list[dict[str, Any]] = Field(min_length=1, max_length=50)


def _scope_statement(user: dict[str, Any], db: Session):
    stmt = select(Report)
    allowed = user_scopes(user)
    if user["role"] == "citizen":
        stmt = stmt.where(Report.reporter_user_id == user["id"])
    elif allowed is not None:
        stmt = stmt.where(Report.district_code.in_(allowed))
    return stmt


@router.get("/reports")
def list_reports(
    db: Session = Depends(get_db),
    user=Depends(require("reports:read")),
    status_filter: str | None = None,
    district_code: str | None = None,
    zone_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    if user["role"] == "researcher":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Researchers receive aggregate statistics only; individual reports are restricted")
    stmt = _scope_statement(user, db)
    if status_filter:
        stmt = stmt.where(Report.status == status_filter.upper())
    if district_code:
        allowed = user_scopes(user)
        if allowed is not None and district_code not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
        stmt = stmt.where(Report.district_code == district_code)
    if zone_id:
        stmt = stmt.where(Report.zone_id == zone_id)
    rows = list(db.execute(stmt.order_by(Report.created_at.desc())).scalars())
    total = len(rows)
    page = rows[offset:offset + limit]
    include_contact = user["role"] in {"platform_admin", "state_admin", "district_admin"}
    return {
        "reports": [report_dict(r, include_contact=include_contact) for r in page],
        "meta": page_bounds(total, limit, offset),
        "pending_verification": sum(1 for r in rows if r.status == "PENDING_VERIFICATION"),
        "note": "Reports enter PENDING_VERIFICATION and never alter hazard until an officer verifies them.",
    }


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db), user=Depends(require("reports:read"))):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    allowed = user_scopes(user)
    if user["role"] == "citizen" and report.reporter_user_id != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your report")
    if allowed is not None and report.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    zone = db.get(SpatialUnit, report.zone_id) if report.zone_id else None
    return {
        **report_dict(report, include_contact=True),
        "zone_name": zone.name if zone else None,
        "district_name": zone.district_code if zone else report.district_code,
    }


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require("reports:create")),
    hazard_type: str = Form(...),
    description: str = Form(""),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    gps_accuracy_m: float | None = Form(None),
    observed_at: str | None = Form(None),
    consent: bool = Form(False),
    anonymous: bool = Form(False),
    client_uuid: str | None = Form(None),
    zone_id: int | None = Form(None),
    reporter_name: str | None = Form(None),
    contact: str | None = Form(None),
    device_id: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    ctx = request_context(request)
    rate_limiter.check(f"report:{user['id']}", settings.rate_limit_write_per_min, 60)
    uploads = [f for f in files if f and f.filename] if files else []
    try:
        report, duplicate = report_service.create_report(
            db,
            payload={
                "hazard_type": hazard_type, "description": description, "lat": lat, "lon": lon,
                "gps_accuracy_m": gps_accuracy_m, "observed_at": observed_at, "consent": consent,
                "anonymous": anonymous, "client_uuid": client_uuid, "zone_id": zone_id,
                "reporter_name": reporter_name, "contact": contact, "device_id": device_id,
            },
            uploads=uploads,
            actor=user,
            sync_source="online",
            request_id=ctx["request_id"],
        )
    except ReportError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return {"report": report_dict(report), "duplicate": duplicate}


@router.post("/reports/sync")
def sync(request: Request, payload: SyncRequest, db: Session = Depends(get_db),
         user=Depends(require("reports:create"))):
    ctx = request_context(request)
    rate_limiter.check(f"sync:{user['id']}", 12, 60)
    result = report_service.sync_reports(db, items=payload.items, actor=user, request_id=ctx["request_id"])
    audit.record(db, actor=user, action="reports.synced", entity="report_batch",
                 entity_id=ctx["request_id"],
                 reason="Offline queue synchronisation",
                 payload={"accepted": result["accepted"], "duplicates": result["duplicates"],
                          "failed": result["failed"]},
                 request_id=ctx["request_id"])
    db.commit()
    return {**result, "note": "A report is only marked synchronized after the server returns its id."}


@router.patch("/reports/{report_id}/verify")
def verify(report_id: int, payload: VerifyRequest, request: Request, db: Session = Depends(get_db),
           user=Depends(require("reports:verify"))):
    ctx = request_context(request)
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    allowed = user_scopes(user)
    if allowed is not None and report.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    try:
        result = report_service.verify_report(
            db, report, decision=payload.decision, note=payload.note, actor=user,
            request_id=ctx["request_id"],
        )
    except ReportError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {
        **result,
        "verified_at": result["verified_at"] or iso(report.verified_at),
        "note": "Verified evidence enters the risk pipeline through a bounded, time-decayed adjustment (max 15 points).",
    }
