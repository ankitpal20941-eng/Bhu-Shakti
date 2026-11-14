"""Audit trail. Every material state change is recorded with actor, reason and request id."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditLog


def record(
    db: Session,
    *,
    actor: dict[str, Any] | None,
    action: str,
    entity: str,
    entity_id: str | int = "",
    reason: str = "",
    payload: dict[str, Any] | None = None,
    request_id: str = "",
    ip: str = "",
) -> AuditLog:
    entry = AuditLog(
        actor_id=(actor or {}).get("id"),
        actor_email=(actor or {}).get("email", "anonymous"),
        actor_role=(actor or {}).get("role", "anonymous"),
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        reason=reason,
        payload=payload or {},
        request_id=request_id,
        ip=ip,
    )
    db.add(entry)
    return entry
