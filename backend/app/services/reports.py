"""Field/citizen reporting, media handling and offline synchronisation.

Safety rule: a report always enters PENDING_VERIFICATION. Only an authorised
verification step can feed hazard adjustment, and that adjustment is bounded.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..engine.exposure import haversine_km
from ..models import Report, ReportMedia, SpatialUnit
from . import audit
from .events import bus
from .util import as_utc, iso

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
}
MAGIC_PREFIXES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
    "video/mp4": (b"\x00\x00\x00", b"ftyp"),
}
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"
CLIENT_UUID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")


class ReportError(ValueError):
    pass


def _detect_type(head: bytes, declared: str | None) -> str:
    declared = (declared or "").lower().split(";")[0].strip()
    if declared not in ALLOWED_TYPES:
        raise ReportError(f"Unsupported media type '{declared or 'unknown'}'. Allowed: JPEG, PNG, WebP, MP4.")
    if not any(head.startswith(prefix) for prefix in MAGIC_PREFIXES[declared]):
        raise ReportError(f"File content does not match declared type {declared}.")
    return declared


def store_media(db: Session, report: Report, uploads: list[Any]) -> list[dict[str, Any]]:
    if len(uploads) > settings.max_uploads_per_report:
        raise ReportError(f"At most {settings.max_uploads_per_report} files per report")
    stored: list[dict[str, Any]] = []
    for upload in uploads:
        raw = upload.file.read(settings.max_upload_bytes + 1)
        if len(raw) > settings.max_upload_bytes:
            raise ReportError(f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB limit")
        if not raw:
            raise ReportError("Empty file")
        if EICAR in raw:
            raise ReportError("Upload rejected by malware scan")
        content_type = _detect_type(raw[:16], upload.content_type)
        digest = hashlib.sha256(raw).hexdigest()
        stamp = datetime.now(timezone.utc)
        rel = Path("reports") / stamp.strftime("%Y") / stamp.strftime("%m") / f"{uuid.uuid4().hex}{ALLOWED_TYPES[content_type]}"
        target = settings.storage_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        media = ReportMedia(
            report_id=report.id,
            storage_key=rel.as_posix(),
            content_type=content_type,
            bytes=len(raw),
            sha256=digest,
        )
        db.add(media)
        stored.append({"content_type": content_type, "bytes": len(raw), "sha256": digest})
    return stored


def _nearest_zone(db: Session, lat: float, lon: float) -> SpatialUnit | None:
    best: tuple[float, SpatialUnit] | None = None
    for zone in db.execute(select(SpatialUnit)).scalars():
        distance = haversine_km(lat, lon, zone.centroid_lat, zone.centroid_lon)
        if best is None or distance < best[0]:
            best = (distance, zone)
    if best and best[0] <= 15.0:
        return best[1]
    return None


def create_report(
    db: Session,
    *,
    payload: dict[str, Any],
    uploads: list[Any] | None = None,
    actor: dict[str, Any] | None,
    sync_source: str = "online",
    request_id: str = "",
) -> tuple[Report, bool]:
    client_uuid = str(payload.get("client_uuid") or uuid.uuid4().hex)
    if not CLIENT_UUID_RE.match(client_uuid):
        raise ReportError("client_uuid must be 8-64 characters of letters, digits or . _ : -")
    existing = db.execute(select(Report).where(Report.client_uuid == client_uuid)).scalars().first()
    if existing is not None:
        return existing, True  # idempotent replay

    lat = payload.get("lat")
    lon = payload.get("lon")
    consent = bool(payload.get("consent"))
    if (lat is not None or uploads) and not consent:
        raise ReportError("Consent is required to store GPS coordinates or media (DPDP Act 2023).")
    if (lat is None) != (lon is None):
        raise ReportError("lat and lon must be provided together")
    if lat is not None and not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        raise ReportError("Coordinates out of range")

    zone: SpatialUnit | None = None
    if payload.get("zone_id"):
        zone = db.get(SpatialUnit, int(payload["zone_id"]))
        if zone is None:
            raise ReportError("Unknown zone_id")
    elif lat is not None:
        zone = _nearest_zone(db, float(lat), float(lon))

    observed = payload.get("observed_at")
    if isinstance(observed, str) and observed:
        try:
            observed_dt = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReportError("observed_at must be ISO-8601") from exc
    else:
        observed_dt = datetime.now(timezone.utc)

    report = Report(
        client_uuid=client_uuid,
        zone_id=zone.id if zone else None,
        district_code=zone.district_code if zone else payload.get("district_code"),
        hazard_type=str(payload.get("hazard_type") or "OTHER").upper(),
        description=str(payload.get("description") or "")[:4000],
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
        gps_accuracy_m=float(payload["gps_accuracy_m"]) if payload.get("gps_accuracy_m") is not None else None,
        observed_at=observed_dt,
        status="PENDING_VERIFICATION",
        anonymous=bool(payload.get("anonymous", True)),
        reporter_user_id=(actor or {}).get("id"),
        reporter_name=payload.get("reporter_name"),
        contact=payload.get("contact"),
        consent=consent,
        device_id=payload.get("device_id"),
        sync_source=sync_source,
    )
    db.add(report)
    db.flush()
    if uploads:
        store_media(db, report, uploads)
    audit.record(db, actor=actor, action="report.created", entity="report", entity_id=report.id,
                 reason="Field hazard report submitted (pending verification)",
                 payload={"hazard_type": report.hazard_type, "zone_id": report.zone_id,
                          "sync_source": sync_source, "anonymous": report.anonymous},
                 request_id=request_id)
    db.commit()
    bus.publish("report.created", {"id": report.id, "status": report.status,
                                   "district_code": report.district_code,
                                   "hazard_type": report.hazard_type})
    return report, False


def verify_report(
    db: Session,
    report: Report,
    *,
    decision: str,
    note: str,
    actor: dict[str, Any],
    request_id: str = "",
) -> dict[str, Any]:
    if report.status != "PENDING_VERIFICATION":
        raise ReportError(f"Report already {report.status}")
    if decision not in {"VERIFIED", "REJECTED"}:
        raise ReportError("decision must be VERIFIED or REJECTED")
    if decision == "REJECTED" and not note.strip():
        raise ReportError("A reason is required to reject a report")
    report.status = decision
    report.verification_note = note.strip()
    report.verified_by = actor["id"]
    report.verified_at = datetime.now(timezone.utc)
    audit.record(db, actor=actor, action=f"report.{decision.lower()}", entity="report",
                 entity_id=report.id, reason=note.strip(),
                 payload={"zone_id": report.zone_id, "hazard_type": report.hazard_type},
                 request_id=request_id)
    db.commit()
    bus.publish("report.created", {"id": report.id, "status": report.status})

    adjustment = 0.0
    if decision == "VERIFIED" and report.district_code:
        from .risk import recalculate  # local import: avoids a cycle

        summary = recalculate(
            db,
            district_codes=[report.district_code],
            actor=actor,
            request_id=request_id,
            reason=f"Verified field report #{report.id} entered the risk pipeline",
        )
        if report.zone_id is not None:
            from ..models import RiskAssessment

            latest = db.execute(
                select(RiskAssessment)
                .where(RiskAssessment.zone_id == report.zone_id, RiskAssessment.is_scenario.is_(False))
                .order_by(RiskAssessment.computed_at.desc()).limit(1)
            ).scalars().first()
            if latest:
                adjustment = float((latest.inputs or {}).get("field_evidence", {}).get("applied_points", 0.0))
        report.risk_adjustment_applied = adjustment
        db.commit()
        summary["field_adjustment_points"] = adjustment
    else:
        summary = {}
    return {
        "id": report.id,
        "status": report.status,
        "verified_at": iso(report.verified_at),
        "field_adjustment_points": adjustment,
        "risk_recalculation": {k: summary[k] for k in ("run_id", "zones_assessed") if k in summary},
    }


def sync_reports(
    db: Session,
    *,
    items: list[dict[str, Any]],
    actor: dict[str, Any] | None,
    request_id: str = "",
) -> dict[str, Any]:
    """Idempotent batch sync for the offline field queue.

    Each item is applied independently; a partial failure never discards the
    successfully stored reports, and the client keeps failed items queued.
    """
    results: list[dict[str, Any]] = []
    accepted = duplicates = failed = 0
    for index, item in enumerate(items):
        payload = item.get("payload") or item
        try:
            report, duplicate = create_report(
                db, payload=payload, actor=actor, sync_source="offline_queue",
                request_id=request_id,
            )
            results.append({
                "index": index,
                "client_uuid": report.client_uuid,
                "status": "duplicate" if duplicate else "accepted",
                "id": report.id,
                "server_status": report.status,
            })
            duplicates += int(duplicate)
            accepted += int(not duplicate)
        except ReportError as exc:
            failed += 1
            results.append({
                "index": index,
                "client_uuid": (payload or {}).get("client_uuid"),
                "status": "rejected",
                "error": str(exc),
            })
    return {"accepted": accepted, "duplicates": duplicates, "failed": failed, "results": results}
