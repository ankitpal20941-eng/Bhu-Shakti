"""Administration: sources, audit, model registry, alert policy, flags, users, health."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import request_context, require
from ..domain import ROLE_LABELS, Role
from ..engine import params as P
from ..models import (
    Alert,
    AlertPolicy,
    AuditLog,
    DataSource,
    District,
    FeatureFlag,
    IngestionRun,
    ModelEvaluation,
    ModelVersion,
    Report,
    ResponseAssignment,
    RiskAssessment,
    SpatialUnit,
    User,
    UserScope,
)
from ..security import hash_password
from ..services import audit
from ..services.events import bus
from ..services.ingestion import ingest_weather
from ..services.serializers import model_dict, source_dict
from ..services.util import iso

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------- data sources
@router.get("/data-sources")
def data_sources(db: Session = Depends(get_db), user=Depends(require("sources:read"))):
    sources = list(db.execute(select(DataSource).order_by(DataSource.category, DataSource.name)).scalars())
    runs = list(db.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(50)).scalars())
    return {
        "sources": [source_dict(s) for s in sources],
        "runs": [
            {
                "id": r.id, "source_id": r.source_id, "status": r.status, "records": r.records,
                "message": r.message, "started_at": iso(r.started_at), "finished_at": iso(r.finished_at),
                "duration_ms": r.duration_ms,
            }
            for r in runs
        ],
        "states": ["LIVE", "CACHED", "STALE", "DEGRADED", "UNAVAILABLE", "SIMULATED"],
        "note": "A source is only LIVE when it is genuinely connected and within its freshness SLA.",
    }


@router.post("/data-sources/{source_id}/ingest")
def ingest_source(source_id: str, request: Request, db: Session = Depends(get_db),
                  user=Depends(require("sources:write"))):
    ctx = request_context(request)
    source = db.get(DataSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Data source not found")
    if source_id not in {"open-meteo-precip", "open-meteo-soil", "sim-rainfall"}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No adapter is implemented for '{source.name}'. It remains UNAVAILABLE; no data will be invented.",
        )
    districts = list(db.execute(select(District)).scalars())
    result = ingest_weather(db, districts=districts, mode="live" if source_id != "sim-rainfall" else "simulated",
                            request_id=ctx["request_id"], actor_email=user["email"])
    audit.record(db, actor=user, action="source.ingest", entity="data_source", entity_id=source_id,
                 reason="Manual ingestion run", payload={"districts": len(districts)},
                 request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    return result


# ---------------------------------------------------------------- audit
@router.get("/audit-logs")
def audit_logs(
    db: Session = Depends(get_db),
    user=Depends(require("audit:read")),
    action: str | None = None,
    entity: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(AuditLog.at.desc()).offset(offset).limit(limit)).scalars())
    return {
        "entries": [
            {
                "id": r.id, "at": iso(r.at), "actor": r.actor_email, "role": r.actor_role,
                "action": r.action, "entity": r.entity, "entity_id": r.entity_id,
                "reason": r.reason, "payload": r.payload, "request_id": r.request_id, "ip": r.ip,
            }
            for r in rows
        ],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


# ---------------------------------------------------------------- models
@router.get("/models")
def models(db: Session = Depends(get_db), user=Depends(require("models:read"))):
    rows = list(db.execute(select(ModelVersion).order_by(ModelVersion.released_at.desc())).scalars())
    evaluations = list(db.execute(select(ModelEvaluation).order_by(ModelEvaluation.evaluated_at.desc())).scalars())
    return {
        "models": [model_dict(m) for m in rows],
        "evaluations": [
            {"model_version": e.model_version, "method": e.method, "status": e.status,
             "metrics": e.metrics, "notes": e.notes, "evaluated_at": iso(e.evaluated_at)}
            for e in evaluations
        ],
        "active_version": P.MODEL_VERSION,
        "parameters": P.PARAMS.documentation(),
        "release_note": (
            "Only the prototype version is executable in this build. Activation of another version is "
            "rejected rather than pretending a model switch occurred."
        ),
    }


@router.post("/models/{version}/activate")
def activate_model(version: str, request: Request, db: Session = Depends(get_db),
                   user=Depends(require("models:write"))):
    ctx = request_context(request)
    model = db.execute(select(ModelVersion).where(ModelVersion.version == version)).scalars().first()
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model version not found")
    if version != P.MODEL_VERSION:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"'{version}' has no executable inference implementation in this build. "
            "Registering a new version requires a fitted, validated pipeline first.",
        )
    audit.record(db, actor=user, action="model.activate", entity="model", entity_id=version,
                 reason="Activation requested; already active", payload={"status": model.status},
                 request_id=ctx["request_id"])
    db.commit()
    return {"active_version": P.MODEL_VERSION, "status": model.status, "changed": False}


@router.post("/models/{version}/rollback")
def rollback_model(version: str, request: Request, db: Session = Depends(get_db),
                   user=Depends(require("models:write"))):
    ctx = request_context(request)
    model = db.execute(select(ModelVersion).where(ModelVersion.version == version)).scalars().first()
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model version not found")
    if version != P.MODEL_VERSION:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only the active prototype can be rolled back to")
    audit.record(db, actor=user, action="model.rollback", entity="model", entity_id=version,
                 reason="Rollback requested; no previous production model exists",
                 request_id=ctx["request_id"])
    db.commit()
    return {
        "active_version": P.MODEL_VERSION,
        "rollback_available": False,
        "note": "No previously released production model exists. This build always runs the prototype.",
    }


# ---------------------------------------------------------------- alert policy
class PolicyInput(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    watch: float = Field(ge=0, le=100)
    warning: float = Field(ge=0, le=100)
    critical: float = Field(ge=0, le=100)
    hysteresis_points: float = Field(default=5, ge=0, le=20)
    min_duration_min: int = Field(default=30, ge=0, le=1440)
    dedupe_window_min: int = Field(default=180, ge=10, le=1440)
    activate: bool = True


@router.get("/alert-policy")
def get_policies(db: Session = Depends(get_db), user=Depends(require("risk:read"))):
    rows = list(db.execute(select(AlertPolicy).order_by(AlertPolicy.created_at.desc())).scalars())
    return {
        "policies": [
            {
                "version": p.version, "name": p.name, "thresholds": p.thresholds,
                "hysteresis_points": p.hysteresis_points, "min_duration_min": p.min_duration_min,
                "dedupe_window_min": p.dedupe_window_min, "active": p.active, "created_at": iso(p.created_at),
            }
            for p in rows
        ],
        "approval_required": True,
        "note": "Thresholds are prototype starting values, not validated operational cut-offs.",
    }


@router.post("/alert-policy", status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyInput, request: Request, db: Session = Depends(get_db),
                  user=Depends(require("flags:write"))):
    ctx = request_context(request)
    if not (payload.watch < payload.warning < payload.critical):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Thresholds must increase: watch < warning < critical")
    version = f"policy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    if payload.activate:
        for existing in db.execute(select(AlertPolicy).where(AlertPolicy.active.is_(True))).scalars():
            existing.active = False
    policy = AlertPolicy(
        version=version, name=payload.name,
        thresholds={"WATCH": payload.watch, "WARNING": payload.warning, "CRITICAL": payload.critical},
        hysteresis_points=payload.hysteresis_points, min_duration_min=payload.min_duration_min,
        dedupe_window_min=payload.dedupe_window_min, active=payload.activate, created_by=user["id"],
    )
    db.add(policy)
    audit.record(db, actor=user, action="alert_policy.created", entity="alert_policy", entity_id=version,
                 reason="New alert policy version", payload={"thresholds": policy.thresholds,
                                                             "active": policy.active},
                 request_id=ctx["request_id"])
    db.commit()
    return {"version": version, "active": policy.active, "thresholds": policy.thresholds}


# ---------------------------------------------------------------- feature flags
@router.get("/feature-flags")
def feature_flags(db: Session = Depends(get_db), user=Depends(require("admin:read"))):
    rows = list(db.execute(select(FeatureFlag).order_by(FeatureFlag.key)).scalars())
    return {
        "flags": [
            {"key": f.key, "enabled": f.enabled, "description": f.description,
             "updated_by": f.updated_by, "updated_at": iso(f.updated_at)}
            for f in rows
        ]
    }


@router.patch("/feature-flags/{key}")
def set_flag(key: str, payload: dict, request: Request, db: Session = Depends(get_db),
             user=Depends(require("flags:write"))):
    ctx = request_context(request)
    flag = db.get(FeatureFlag, key)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown feature flag")
    if "enabled" not in payload:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Body must contain 'enabled'")
    before = flag.enabled
    flag.enabled = bool(payload["enabled"])
    flag.updated_by = user["email"]
    audit.record(db, actor=user, action="feature_flag.updated", entity="feature_flag", entity_id=key,
                 reason=str(payload.get("reason", "Feature flag updated")),
                 payload={"before": before, "after": flag.enabled}, request_id=ctx["request_id"])
    db.commit()
    return {"key": key, "enabled": flag.enabled}


# ---------------------------------------------------------------- users
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    role: Role
    password: str = Field(min_length=12, max_length=200)
    districts: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: Role | None = None
    districts: list[str] | None = None
    reason: str = Field(default="", max_length=500)


@router.get("/users")
def users(db: Session = Depends(get_db), user=Depends(require("users:read"))):
    rows = list(db.execute(select(User).order_by(User.role_code, User.name)).scalars())
    scopes: dict[int, list[str]] = {}
    for scope in db.execute(select(UserScope)).scalars():
        scopes.setdefault(scope.user_id, []).append(scope.district_code)
    return {
        "users": [
            {
                "id": u.id, "email": u.email, "name": u.name, "role": u.role_code,
                "role_label": ROLE_LABELS.get(u.role_code, u.role_code),
                "districts": scopes.get(u.id, []), "is_active": u.is_active,
                "last_login_at": iso(u.last_login_at), "created_at": iso(u.created_at),
            }
            for u in rows
        ],
        "roles": [{"role": code, "label": label} for code, label in ROLE_LABELS.items()],
        "districts": [
            {"code": d.code, "name": d.name, "state": d.state}
            for d in db.execute(select(District)).scalars()
        ],
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db),
                user=Depends(require("users:write"))):
    ctx = request_context(request)
    if db.execute(select(User).where(User.email == payload.email.lower())).scalars().first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    known = {d.code for d in db.execute(select(District)).scalars()}
    missing = [c for c in payload.districts if c not in known]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown districts: {missing}")
    created = User(email=payload.email.lower(), name=payload.name, role_code=payload.role.value,
                   password_hash=hash_password(payload.password), is_active=True)
    db.add(created)
    db.flush()
    for code in payload.districts:
        db.add(UserScope(user_id=created.id, district_code=code))
    audit.record(db, actor=user, action="user.created", entity="user", entity_id=created.id,
                 reason="User provisioned",
                 payload={"email": created.email, "role": created.role_code,
                          "districts": payload.districts},
                 request_id=ctx["request_id"])
    db.commit()
    return {"id": created.id, "email": created.email, "role": created.role_code}


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db),
                user=Depends(require("users:write"))):
    ctx = request_context(request)
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    before = {"is_active": target.is_active, "role": target.role_code}
    if payload.is_active is not None:
        if target.id == user["id"] and payload.is_active is False:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "You cannot deactivate your own account")
        target.is_active = payload.is_active
    if payload.role is not None:
        target.role_code = payload.role.value
    if payload.districts is not None:
        known = {d.code for d in db.execute(select(District)).scalars()}
        missing = [c for c in payload.districts if c not in known]
        if missing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown districts: {missing}")
        for scope in db.execute(select(UserScope).where(UserScope.user_id == target.id)).scalars():
            db.delete(scope)
        db.flush()
        for code in payload.districts:
            db.add(UserScope(user_id=target.id, district_code=code))
    audit.record(db, actor=user, action="user.updated", entity="user", entity_id=target.id,
                 reason=payload.reason or "User updated",
                 payload={"before": before,
                          "after": {"is_active": target.is_active, "role": target.role_code,
                                    "districts": payload.districts}}, request_id=ctx["request_id"])
    db.commit()
    return {"id": target.id, "is_active": target.is_active, "role": target.role_code}


# ---------------------------------------------------------------- health
@router.get("/system-health")
def system_health(db: Session = Depends(get_db), user=Depends(require("admin:read"))):
    counts = {
        "zones": db.execute(select(func.count()).select_from(SpatialUnit)).scalar_one(),
        "assessments": db.execute(select(func.count()).select_from(RiskAssessment)).scalar_one(),
        "alerts": db.execute(select(func.count()).select_from(Alert)).scalar_one(),
        "reports": db.execute(select(func.count()).select_from(Report)).scalar_one(),
        "assignments": db.execute(select(func.count()).select_from(ResponseAssignment)).scalar_one(),
        "users": db.execute(select(func.count()).select_from(User)).scalar_one(),
    }
    sources = list(db.execute(select(DataSource)).scalars())
    return {
        "status": "ok",
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "ingestion_enabled": settings.ingestion_enabled,
        "weather_mode": settings.weather_mode,
        "model_version": P.MODEL_VERSION,
        "counts": counts,
        "sources": [{"id": s.id, "state": s.state, "age_minutes": None,
                     "last_success_at": iso(s.last_success_at), "last_error": s.last_error}
                    for s in sources],
        "sse_subscribers": bus.subscriber_count,
        "checked_at": iso(datetime.now(timezone.utc)),
    }
