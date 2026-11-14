"""API serialisation helpers. Keeping shapes in one place keeps the UI predictable."""

from __future__ import annotations

from typing import Any

from ..domain import (
    ALERT_DISCLAIMER,
    PRIORITY_LABELS,
    SAFETY_DISCLAIMER,
    Role,
    ROLE_LABELS,
)
from ..engine import params as P
from ..models import (
    Alert,
    AlertDelivery,
    DataSource,
    District,
    ModelVersion,
    Report,
    ResponseAssignment,
    RiskAssessment,
    RoadSegment,
    SpatialUnit,
    User,
)
from .util import iso, minutes_since


def user_public(user: User, scopes: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role_code,
        "role_label": ROLE_LABELS.get(user.role_code, user.role_code),
        "districts": scopes or [],
        "statewide": user.role_code in {Role.PLATFORM_ADMIN, Role.STATE_ADMIN},
    }


def district_dict(district: District) -> dict[str, Any]:
    return {
        "code": district.code,
        "name": district.name,
        "state": district.state,
        "state_code": district.state_code,
        "lat": district.lat,
        "lon": district.lon,
        "bbox": district.bbox_json,
        "boundary_source": district.boundary_source,
        "boundary_note": district.boundary_note,
        "geometry": district.geometry,
        "population_estimate": district.population_estimate,
    }


def zone_summary(zone: SpatialUnit, district: District, assessment: RiskAssessment | None) -> dict[str, Any]:
    return {
        "id": zone.id,
        "code": zone.code,
        "name": zone.name,
        "kind": zone.kind,
        "district_code": zone.district_code,
        "district_name": district.name,
        "state": district.state,
        "centroid": {"lat": zone.centroid_lat, "lon": zone.centroid_lon},
        "area_km2": zone.area_km2,
        "geometry": zone.geometry,
        "hazard_index": assessment.hazard_index if assessment else None,
        "hazard_level": assessment.hazard_level if assessment else None,
        "hazard_probability": None,
        "probability_status": "NOT_CALIBRATED",
        "priority_level": assessment.priority_level if assessment else None,
        "priority_label": PRIORITY_LABELS.get(assessment.priority_level, "") if assessment else "",
        "exposure_score": assessment.exposure_score if assessment else None,
        "vulnerability_score": assessment.vulnerability_score if assessment else None,
        "coverage_level": assessment.coverage_level if assessment else None,
        "susceptibility_index": (
            ((assessment.inputs or {}).get("static") or {}).get("index") if assessment else None
        ),
        "weather_source_state": assessment.weather_source_state if assessment else None,
        "computed_at": iso(assessment.computed_at) if assessment else None,
        "data_age_minutes": assessment.data_age_minutes if assessment else None,
        "out_of_domain": assessment.out_of_domain if assessment else False,
        "model_version": assessment.model_version if assessment else P.MODEL_VERSION,
        "terrain": {
            "elevation_m": zone.elevation_m,
            "slope_deg": zone.slope_deg,
            "aspect_deg": zone.aspect_deg,
            "curvature": zone.curvature,
            "ruggedness": zone.terrain_ruggedness,
            "twi": zone.twi,
            "landcover": zone.landcover,
            "geology": zone.geology,
        },
    }


def zone_detail(
    zone: SpatialUnit,
    district: District,
    assessment: RiskAssessment | None,
    *,
    incidents: list[dict[str, Any]] | None = None,
    reports: list[Report] | None = None,
    segments: list[RoadSegment] | None = None,
    trajectory: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = zone_summary(zone, district, assessment)
    inputs = (assessment.inputs or {}) if assessment else {}
    drivers = (assessment.drivers or {}) if assessment else {}
    base.update({
        "model_version": assessment.model_version if assessment else P.MODEL_VERSION,
        "inputs": inputs,
        "drivers": drivers,
        "priority": inputs.get("priority"),
        "exposure": inputs.get("exposure"),
        "vulnerability": inputs.get("vulnerability"),
        "coverage": inputs.get("coverage"),
        "field_evidence": inputs.get("field_evidence"),
        "recommended_action": inputs.get("recommended_action"),
        "trajectory": trajectory,
        "incidents": incidents or [],
        "reports": [report_dict(r) for r in (reports or [])],
        "road_segments": [segment_dict(s) for s in (segments or [])],
        "history": history or [],
        "provenance": {
            "terrain": zone.terrain_source,
            "landcover": zone.landcover_source,
            "geology": zone.geology_source,
            "weather": (inputs or {}).get("weather_source_id"),
            "model": assessment.model_version if assessment else P.MODEL_VERSION,
        },
        "disclaimer": SAFETY_DISCLAIMER,
    })
    return base


def segment_dict(segment: RoadSegment) -> dict[str, Any]:
    return {
        "id": segment.id,
        "road_id": segment.road_id,
        "zone_id": segment.zone_id,
        "name": segment.name,
        "length_km": segment.length_km,
        "status": segment.status,
        "status_source": segment.status_source,
        "status_updated_at": iso(segment.status_updated_at),
        "evidence": segment.evidence,
        "model_risk_level": segment.model_risk_level,
    }


def report_dict(report: Report, *, include_contact: bool = False) -> dict[str, Any]:
    return {
        "id": report.id,
        "client_uuid": report.client_uuid,
        "zone_id": report.zone_id,
        "district_code": report.district_code,
        "hazard_type": report.hazard_type,
        "description": report.description,
        "lat": report.lat,
        "lon": report.lon,
        "gps_accuracy_m": report.gps_accuracy_m,
        "observed_at": iso(report.observed_at),
        "status": report.status,
        "anonymous": report.anonymous,
        "reporter": report.reporter_name if include_contact else ("Anonymous" if report.anonymous else "Reported user"),
        "contact": report.contact if include_contact else None,
        "media_count": len(report.media),
        "media": [{"id": m.id, "content_type": m.content_type, "bytes": m.bytes,
                   "sha256": m.sha256[:16]} for m in report.media],
        "verification_note": report.verification_note,
        "verified_at": iso(report.verified_at),
        "risk_adjustment_applied": report.risk_adjustment_applied,
        "sync_source": report.sync_source,
        "created_at": iso(report.created_at),
    }


def alert_dict(
    alert: Alert,
    zone: SpatialUnit | None = None,
    district: District | None = None,
    deliveries: list[AlertDelivery] | None = None,
) -> dict[str, Any]:
    return {
        "id": alert.id,
        "reference": alert.reference,
        "zone_id": alert.zone_id,
        "zone_name": zone.name if zone else None,
        "district_code": zone.district_code if zone else None,
        "district_name": district.name if district else None,
        "state": district.state if district else None,
        "severity": alert.severity,
        "status": alert.status,
        "headline": alert.headline,
        "reason": alert.reason,
        "instructions": alert.instructions,
        "onset": iso(alert.onset),
        "expires": iso(alert.expires),
        "geometry": alert.geometry,
        "threatened_assets": alert.threatened_assets,
        "source": alert.source,
        "disclaimer": alert.disclaimer or ALERT_DISCLAIMER,
        "template_version": alert.template_version,
        "language": alert.language,
        "hazard_index": alert.hazard_index,
        "priority_level": alert.priority_level,
        "policy_version": alert.policy_version,
        "is_scenario": alert.is_scenario,
        "created_at": iso(alert.created_at),
        "approved_at": iso(alert.approved_at),
        "rejected_at": iso(alert.rejected_at),
        "rejection_reason": alert.rejection_reason,
        "cancelled_at": iso(alert.cancelled_at),
        "cancel_reason": alert.cancel_reason,
        "deliveries": [
            {
                "channel": d.channel,
                "language": d.language,
                "status": d.status,
                "detail": d.detail,
                "template_version": d.template_version,
                "delivered_at": iso(d.delivered_at),
            }
            for d in (deliveries or [])
        ],
    }


def assignment_dict(
    assignment: ResponseAssignment,
    zone: SpatialUnit | None = None,
    assignee: User | None = None,
    assessment: RiskAssessment | None = None,
) -> dict[str, Any]:
    return {
        "id": assignment.id,
        "zone_id": assignment.zone_id,
        "zone_name": zone.name if zone else None,
        "district_code": zone.district_code if zone else None,
        "alert_id": assignment.alert_id,
        "title": assignment.title,
        "priority": assignment.priority,
        "priority_label": PRIORITY_LABELS.get(assignment.priority, ""),
        "status": assignment.status,
        "assigned_to": assignment.assigned_to,
        "assignee_name": assignee.name if assignee else None,
        "notes": assignment.notes,
        "reason": assignment.reason,
        "due_at": iso(assignment.due_at),
        "created_at": iso(assignment.created_at),
        "updated_at": iso(assignment.updated_at),
        "closed_at": iso(assignment.closed_at),
        "hazard_index": assessment.hazard_index if assessment else None,
        "hazard_level": assessment.hazard_level if assessment else None,
        "exposure_score": assessment.exposure_score if assessment else None,
        "vulnerability_score": assessment.vulnerability_score if assessment else None,
        "recommended_action": ((assessment.inputs or {}).get("recommended_action") if assessment else None),
    }


def source_dict(source: DataSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "name": source.name,
        "category": source.category,
        "provider": source.provider,
        "licence": source.licence,
        "attribution": source.attribution,
        "spatial_resolution": source.spatial_resolution,
        "temporal_resolution": source.temporal_resolution,
        "expected_refresh_min": source.expected_refresh_min,
        "freshness_sla_min": source.freshness_sla_min,
        "fallback_source": source.fallback_source,
        "state": source.state,
        "last_success_at": iso(source.last_success_at),
        "last_attempt_at": iso(source.last_attempt_at),
        "last_error": source.last_error,
        "enabled": source.enabled,
        "notes": source.notes,
        "coverage": source.coverage,
        "age_minutes": minutes_since(source.last_success_at),
    }


def model_dict(model: ModelVersion) -> dict[str, Any]:
    return {
        "version": model.version,
        "kind": model.kind,
        "name": model.name,
        "features": model.features,
        "training_period": model.training_period,
        "spatial_coverage": model.spatial_coverage,
        "validation_approach": model.validation_approach,
        "status": model.status,
        "metrics": model.metrics,
        "card": model.card,
        "released_at": iso(model.released_at),
        "changelog": model.changelog,
    }
