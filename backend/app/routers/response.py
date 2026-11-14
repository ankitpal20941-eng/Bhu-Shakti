"""Response centre: assignments, lifecycle transitions and audit trail."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..domain import ASSIGNMENT_FLOW, AssignmentStatus, PriorityLevel
from ..models import (
    District,
    ResponseAssignment,
    RiskAssessment,
    SpatialUnit,
    User,
)
from ..services import audit, risk as risk_service
from ..services.events import bus
from ..services.serializers import assignment_dict

router = APIRouter(prefix="/api/v1", tags=["response"])


class AssignRequest(BaseModel):
    zone_id: int
    assigned_to: int | None = None
    title: str | None = Field(default=None, max_length=240)
    priority: PriorityLevel | None = None
    notes: str = Field(default="", max_length=2000)
    reason: str = Field(min_length=4, max_length=1000)
    due_at: datetime | None = None


class UpdateRequest(BaseModel):
    status: AssignmentStatus | None = None
    priority: PriorityLevel | None = None
    assigned_to: int | None = None
    notes: str | None = Field(default=None, max_length=2000)
    reason: str = Field(default="", max_length=1000)


def _assignment_context(db: Session, assignment_id: int, user: dict):
    assignment = db.get(ResponseAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    zone = db.get(SpatialUnit, assignment.zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    allowed = user_scopes(user)
    if allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    return assignment, zone


@router.get("/response")
def list_assignments(
    db: Session = Depends(get_db),
    user=Depends(require("response:read")),
    status_filter: str | None = None,
    district_code: str | None = None,
    assigned_to: int | None = None,
    limit: int = Query(default=200, ge=1, le=500),
):
    allowed = user_scopes(user)
    stmt = select(ResponseAssignment)
    if status_filter:
        stmt = stmt.where(ResponseAssignment.status == status_filter.upper())
    if assigned_to:
        stmt = stmt.where(ResponseAssignment.assigned_to == assigned_to)
    rows = list(db.execute(stmt.order_by(ResponseAssignment.created_at.desc())).scalars())
    zones = {z.id: z for z in db.execute(select(SpatialUnit)).scalars()}
    assignees = {u.id: u for u in db.execute(select(User)).scalars()}
    assessments = risk_service.latest_assessments(db, {a.zone_id for a in rows})
    out = []
    for assignment in rows:
        zone = zones.get(assignment.zone_id)
        if zone is None:
            continue
        if allowed is not None and zone.district_code not in allowed:
            continue
        if district_code and zone.district_code != district_code:
            continue
        out.append(assignment_dict(assignment, zone, assignees.get(assignment.assigned_to),
                                   assessments.get(assignment.zone_id)))
    return {
        "assignments": out[:limit],
        "counts": {
            status_value.value: sum(1 for a in out if a["status"] == status_value.value)
            for status_value in AssignmentStatus
        },
        "lifecycle": [s.value for s in AssignmentStatus],
        "flow": {k.value: [v.value for v in vals] for k, vals in ASSIGNMENT_FLOW.items()},
    }


@router.post("/response/assign", status_code=status.HTTP_201_CREATED)
def assign(payload: AssignRequest, request: Request, db: Session = Depends(get_db),
           user=Depends(require("response:write"))):
    ctx = request_context(request)
    zone = db.get(SpatialUnit, payload.zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    allowed = user_scopes(user)
    if allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")

    assignee = None
    if payload.assigned_to is not None:
        assignee = db.get(User, payload.assigned_to)
        if assignee is None or not assignee.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assignee not found or inactive")
        if assignee.role_code not in {"field_officer", "district_admin", "analyst"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "Assignee must be a field officer, analyst or district administrator")

    assessment = risk_service.latest_assessment(db, zone.id)
    assignment = ResponseAssignment(
        zone_id=zone.id,
        title=payload.title or f"Inspection — {zone.name}",
        priority=(payload.priority.value if payload.priority else (assessment.priority_level if assessment else "P3")),
        status=AssignmentStatus.ASSIGNED.value if payload.assigned_to else AssignmentStatus.DETECTED.value,
        assigned_to=payload.assigned_to,
        assigned_by=user["id"],
        notes=payload.notes,
        reason=payload.reason,
        due_at=payload.due_at,
    )
    db.add(assignment)
    db.flush()
    audit.record(db, actor=user, action="assignment.created", entity="assignment",
                 entity_id=assignment.id, reason=payload.reason,
                 payload={"zone_id": zone.id, "assigned_to": payload.assigned_to,
                          "priority": assignment.priority, "status": assignment.status},
                 request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    bus.publish("assignment.updated", {"id": assignment.id, "status": assignment.status,
                                       "zone_id": zone.id})
    return assignment_dict(assignment, zone, assignee, assessment)


@router.patch("/response/{assignment_id}")
def update(assignment_id: int, payload: UpdateRequest, request: Request, db: Session = Depends(get_db),
           user=Depends(require("response:write"))):
    ctx = request_context(request)
    assignment, zone = _assignment_context(db, assignment_id, user)

    if assignment.assigned_to and user["role"] == "field_officer" and assignment.assigned_to != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Field officers may only update their own assignments")

    before = {"status": assignment.status, "priority": assignment.priority,
              "assigned_to": assignment.assigned_to, "notes": assignment.notes}

    if payload.status and payload.status.value != assignment.status:
        allowed_next = {s.value for s in ASSIGNMENT_FLOW.get(AssignmentStatus(assignment.status), ())}
        if payload.status.value not in allowed_next:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Illegal lifecycle transition {assignment.status} -> {payload.status.value}. "
                f"Allowed: {sorted(allowed_next) or 'none'}",
            )
        assignment.status = payload.status.value
        if payload.status in {AssignmentStatus.RESOLVED}:
            assignment.closed_at = datetime.now(timezone.utc)
    if payload.priority and payload.priority.value != assignment.priority:
        if not payload.reason.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "A reason is required when changing priority")
        assignment.priority = payload.priority.value
    if payload.assigned_to is not None and payload.assigned_to != assignment.assigned_to:
        assignee = db.get(User, payload.assigned_to)
        if assignee is None or not assignee.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assignee not found")
        assignment.assigned_to = payload.assigned_to
        if assignment.status == AssignmentStatus.DETECTED.value:
            assignment.status = AssignmentStatus.ASSIGNED.value
    if payload.notes is not None:
        assignment.notes = payload.notes
    assignment.reason = payload.reason or assignment.reason
    assignment.updated_at = datetime.now(timezone.utc)

    audit.record(db, actor=user, action="assignment.updated", entity="assignment", entity_id=assignment.id,
                 reason=payload.reason or "Assignment updated",
                 payload={"before": before, "after": {"status": assignment.status,
                                                      "priority": assignment.priority,
                                                      "assigned_to": assignment.assigned_to}},
                 request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    bus.publish("assignment.updated", {"id": assignment.id, "status": assignment.status,
                                       "zone_id": zone.id})
    assignee = db.get(User, assignment.assigned_to) if assignment.assigned_to else None
    assessment = risk_service.latest_assessment(db, zone.id)
    return assignment_dict(assignment, zone, assignee, assessment)
