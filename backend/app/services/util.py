"""Small shared helpers for timezone-safe serialisation and pagination."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso(value: datetime | None) -> str | None:
    dt = as_utc(value)
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def minutes_since(value: datetime | None, now: datetime | None = None) -> int | None:
    dt = as_utc(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, int((now - dt).total_seconds() // 60))


def days_since(value: datetime | None, now: datetime | None = None) -> int | None:
    minutes = minutes_since(value, now)
    return None if minutes is None else minutes // 1440


def page_bounds(total: int, limit: int, offset: int) -> dict[str, Any]:
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }
