"""FastAPI dependencies: request context, session user, permission guards."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, UserScope
from .security import decode_token, ensure_permission, token_from_request


def request_context(request: Request) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", "") or request.headers.get("x-request-id", "")
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")
    return {"request_id": request_id, "ip": ip}


def _load_scopes(db: Session, user_id: int) -> list[str]:
    return [row.district_code for row in db.execute(
        select(UserScope).where(UserScope.user_id == user_id)
    ).scalars()]


def _user_from_token(db: Session, token: str) -> dict[str, Any]:
    payload = decode_token(token)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is not active")
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role_code,
        "scopes": _load_scopes(db, user.id),
        "token": payload,
    }


def optional_user(request: Request, db: Session = Depends(get_db)) -> dict[str, Any] | None:
    token = token_from_request(request)
    if not token:
        return None
    try:
        return _user_from_token(db, token)
    except HTTPException:
        return None


def current_user(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    token = token_from_request(request)
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_from_token(db, token)


def require(permission: str) -> Callable[..., dict[str, Any]]:
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        ensure_permission(user["role"], permission)
        return user

    return dependency


def user_scopes(user: dict[str, Any]) -> list[str] | None:
    """None means statewide/all-district access."""
    if user["role"] in {"platform_admin", "state_admin", "citizen", "researcher"}:
        return None
    return user["scopes"]
