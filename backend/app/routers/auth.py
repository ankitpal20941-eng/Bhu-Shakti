"""Authentication endpoints (cookie session for the app, Bearer token for API/PWA)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user, request_context
from ..domain import ROLE_LABELS, permissions_for
from ..models import User
from ..security import create_token, rate_limiter, verify_password
from ..services import audit
from ..services.serializers import user_public
from ..services.util import iso

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ctx = request_context(request)
    rate_limiter.check(f"login:{ctx['ip']}", settings.rate_limit_login_per_min, 60)
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalars().first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        audit.record(db, actor=None, action="auth.login_failed", entity="user",
                     entity_id=payload.email, reason="invalid credentials",
                     request_id=ctx["request_id"], ip=ctx["ip"])
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    scopes = [s.district_code for s in user.scopes] if hasattr(user, "scopes") else []
    from ..models import UserScope

    scopes = [row.district_code for row in db.execute(
        select(UserScope).where(UserScope.user_id == user.id)
    ).scalars()]
    token, expires = create_token(user_id=user.id, email=user.email, role=user.role_code, scopes=scopes)
    user.last_login_at = datetime.now(timezone.utc)
    audit.record(db, actor={"id": user.id, "email": user.email, "role": user.role_code},
                 action="auth.login", entity="user", entity_id=user.id,
                 reason="successful login", request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    response.set_cookie(
        settings.session_cookie, token, httponly=True, samesite="lax", secure=settings.is_production,
        max_age=settings.session_ttl_minutes * 60, path="/",
    )
    return {
        "token": token,
        "expires_at": iso(expires),
        "user": user_public(user, scopes),
        "permissions": sorted(permissions_for(user.role_code)),
    }


@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db),
           user=Depends(current_user)):
    ctx = request_context(request)
    audit.record(db, actor=user, action="auth.logout", entity="user", entity_id=user["id"],
                 reason="logout", request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user)):
    return {
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "role": user["role"], "role_label": ROLE_LABELS.get(user["role"], user["role"]),
            "districts": user["scopes"],
            "statewide": user["role"] in {"platform_admin", "state_admin"},
        },
        "permissions": sorted(permissions_for(user["role"])),
    }


@router.get("/demo-accounts")
def demo_accounts():
    """Only available in demo mode; documents the seeded pilot accounts."""
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available")
    return {
        "mode": "DEMO",
        "warning": "Demonstration accounts. Never enable seeded accounts in production.",
        "accounts": [
            {"email": "admin@bhushakti.demo", "role": "Platform Administrator"},
            {"email": "state.assam@bhushakti.demo", "role": "State Administrator (Assam)"},
            {"email": "dc.kamrup@bhushakti.demo", "role": "District Administrator (Kamrup Metro)"},
            {"email": "analyst@bhushakti.demo", "role": "Authority Analyst"},
            {"email": "field.officer@bhushakti.demo", "role": "Field Officer (Kamrup Metro)"},
            {"email": "citizen@bhushakti.demo", "role": "Citizen"},
            {"email": "researcher@bhushakti.demo", "role": "Researcher"},
        ],
        "password_hint": "See README 'Demo credentials'. Passwords are seeded only in demo mode.",
    }
