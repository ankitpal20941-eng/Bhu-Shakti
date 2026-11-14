"""Authentication primitives: PBKDF2 password hashing and signed session tokens.

Tokens are HMAC-SHA256 signed (JWT-shaped, no external JWT dependency) and are
accepted either as an httpOnly cookie (browser) or a Bearer header (API clients,
field PWA background sync).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status

from .config import settings
from .domain import can, permissions_for

PBKDF2_ITERATIONS = 240_000
_TOKEN_VERSION = 1


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, digest_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(payload_b64: str) -> str:
    sig = hmac.new(settings.secret_key.encode(), payload_b64.encode(), hashlib.sha256).digest()
    return _b64e(sig)


def create_token(*, user_id: int, email: str, role: str, scopes: list[str]) -> tuple[str, datetime]:
    issued = datetime.now(timezone.utc)
    expires = issued + timedelta(minutes=settings.session_ttl_minutes)
    payload = {
        "v": _TOKEN_VERSION,
        "sub": user_id,
        "email": email,
        "role": role,
        "scopes": scopes,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_hex(8),
    }
    payload_b64 = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return f"{payload_b64}.{_sign(payload_b64)}", expires


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload_b64, signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed session token") from exc
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session signature")
    try:
        payload = json.loads(_b64d(payload_b64))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed session payload") from exc
    if payload.get("v") != _TOKEN_VERSION:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unsupported session version")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return payload


def token_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    cookie = request.cookies.get(settings.session_cookie)
    return cookie or None


def ensure_permission(role: str, permission: str) -> None:
    if not can(role, permission):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Role '{role}' lacks permission '{permission}'",
        )


class RateLimiter:
    """In-process sliding-window limiter. Production should use Redis."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, limit: int, window_s: int = 60) -> None:
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < window_s]
        if len(hits) >= limit:
            self._hits[key] = hits
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded; retry shortly")
        hits.append(now)
        self._hits[key] = hits


rate_limiter = RateLimiter()


def scope_districts(user: dict) -> list[str] | None:
    """Return the district codes a user may access, or None for statewide access."""
    role = user.get("role")
    if role in {"platform_admin", "state_admin"}:
        return None
    scopes = user.get("scopes") or []
    if role == "citizen":
        return None
    return list(scopes)


def assert_district_access(user: dict, district_code: str | None) -> None:
    allowed = scope_districts(user)
    if allowed is None or district_code is None:
        return
    if district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")


def assert_zone_access(db, user: dict, zone_id: int) -> str:
    from .models import SpatialUnit

    zone = db.get(SpatialUnit, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    assert_district_access(user, zone.district_code)
    return zone.district_code


def permissions_summary(role: str) -> dict[str, Any]:
    return {"role": role, "permissions": sorted(permissions_for(role))}
