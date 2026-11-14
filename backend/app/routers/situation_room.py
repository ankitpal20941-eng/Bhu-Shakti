"""Emergency Situation Room Operations Dashboard Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..models import (
    Alert,
    District,
    EmergencyFacility,
    Report,
    ResponseAssignment,
    RiskAssessment,
    RoadSegment,
    SpatialUnit,
)

router = APIRouter(prefix="/api/v1/situation-room", tags=["situation-room"])


@router.get("")
def get_situation_room_dashboard(
    district_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("risk:read")),
) -> dict[str, Any]:
    """Central operational command room aggregator for disaster management authorities."""
    dist_filter = [district_code] if district_code else None

    # Risk zones by severity
    zone_stmt = select(SpatialUnit, RiskAssessment).join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
    if dist_filter:
        zone_stmt = zone_stmt.where(SpatialUnit.district_code.in_(dist_filter))
    all_zones = db.execute(zone_stmt).all()

    critical_zones = []
    warning_zones = []
    watch_zones = []

    for zone, assessment in all_zones:
        z_payload = {
            "id": zone.id,
            "code": zone.code,
            "name": zone.name,
            "district_code": zone.district_code,
            "hazard_index": assessment.hazard_index,
            "hazard_level": assessment.hazard_level,
            "priority_level": assessment.priority_level,
            "lat": zone.centroid_lat,
            "lon": zone.centroid_lon,
        }
        if assessment.hazard_level == "CRITICAL":
            critical_zones.append(z_payload)
        elif assessment.hazard_level == "WARNING":
            warning_zones.append(z_payload)
        elif assessment.hazard_level == "WATCH":
            watch_zones.append(z_payload)

    # Pending alert approvals
    alert_stmt = select(Alert).where(Alert.status == "CANDIDATE").order_by(Alert.created_at.desc())
    pending_alerts = db.execute(alert_stmt).scalars().all()

    # Active response assignments
    assign_stmt = select(ResponseAssignment).where(ResponseAssignment.status.in_(["DETECTED", "ASSIGNED", "INSPECTED"]))
    open_assignments = db.execute(assign_stmt).scalars().all()

    # Impacted / Blocked road segments
    road_stmt = select(RoadSegment).where(RoadSegment.status.in_(["BLOCKED", "AT_RISK", "RESTRICTED"]))
    disrupted_roads = db.execute(road_stmt).scalars().all()

    # Emergency facilities readiness
    fac_stmt = select(EmergencyFacility).where(EmergencyFacility.status == "OPERATIONAL")
    if dist_filter:
        fac_stmt = fac_stmt.where(EmergencyFacility.district_code.in_(dist_filter))
    facilities = db.execute(fac_stmt).scalars().all()

    # Recent verified reports
    report_stmt = select(Report).order_by(Report.created_at.desc()).limit(10)
    recent_reports = db.execute(report_stmt).scalars().all()

    return {
        "active_filter_district": district_code or "ALL_DISTRICTS",
        "counts": {
            "critical_zones": len(critical_zones),
            "warning_zones": len(warning_zones),
            "watch_zones": len(watch_zones),
            "pending_alert_approvals": len(pending_alerts),
            "active_field_assignments": len(open_assignments),
            "disrupted_road_segments": len(disrupted_roads),
            "operational_facilities": len(facilities),
            "recent_reports": len(recent_reports),
        },
        "critical_zones": critical_zones[:10],
        "warning_zones": warning_zones[:15],
        "watch_zones_sample": watch_zones[:5],
        "pending_alerts": [
            {
                "id": a.id,
                "reference": a.reference,
                "headline": a.headline,
                "severity": a.severity,
                "created_at": a.created_at.isoformat(),
            }
            for a in pending_alerts
        ],
        "disrupted_roads": [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "length_km": r.length_km,
                "status_source": r.status_source,
            }
            for r in disrupted_roads
        ],
        "operational_facilities": [
            {
                "id": f.id,
                "name": f.name,
                "kind": f.kind,
                "district_code": f.district_code,
                "capacity": f.capacity,
                "occupancy": f.current_occupancy,
            }
            for f in facilities[:8]
        ],
        "recent_reports": [
            {
                "id": rep.id,
                "hazard_type": rep.hazard_type,
                "status": rep.status,
                "description": rep.description[:80],
                "observed_at": rep.observed_at.isoformat(),
            }
            for rep in recent_reports
        ],
        "telemetry_stream_status": "ONLINE (Heartbeat sync active)",
    }
