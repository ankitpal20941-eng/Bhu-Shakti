"""Domain vocabulary, permissions and policy thresholds.

All thresholds in this module are PROTOTYPE defaults. They are configurable and
versioned; they are not validated operational warning thresholds.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    STATE_ADMIN = "state_admin"
    DISTRICT_ADMIN = "district_admin"
    ANALYST = "analyst"
    FIELD_OFFICER = "field_officer"
    CITIZEN = "citizen"
    RESEARCHER = "researcher"


ROLE_LABELS: dict[str, str] = {
    Role.PLATFORM_ADMIN: "Platform Administrator",
    Role.STATE_ADMIN: "State Administrator",
    Role.DISTRICT_ADMIN: "District Administrator",
    Role.ANALYST: "Authority Analyst",
    Role.FIELD_OFFICER: "Field Officer",
    Role.CITIZEN: "Citizen",
    Role.RESEARCHER: "Researcher",
}

# Explicit permission matrix. Enforced server-side on every protected route.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.PLATFORM_ADMIN: frozenset({
        "risk:read", "risk:recalculate", "zone:read", "weather:read", "roads:read", "roads:write",
        "infra:read", "incidents:read", "reports:read", "reports:create", "reports:verify",
        "alerts:read", "alerts:prepare", "alerts:approve", "alerts:cancel",
        "response:read", "response:write", "scenarios:run", "analytics:read", "analytics:export",
        "admin:read", "admin:write", "models:read", "models:write", "audit:read",
        "sources:read", "sources:write", "users:read", "users:write", "flags:write",
        "facilities:read", "facilities:write", "teams:read", "teams:write", "quality:read",
        "satellite:read", "satellite:verify", "notifications:read", "notifications:send",
        "replay:read", "runout:read",
    }),
    Role.STATE_ADMIN: frozenset({
        "risk:read", "risk:recalculate", "zone:read", "weather:read", "roads:read", "roads:write",
        "infra:read", "incidents:read", "reports:read", "reports:create", "reports:verify",
        "alerts:read", "alerts:prepare", "alerts:approve", "alerts:cancel",
        "response:read", "response:write", "scenarios:run", "analytics:read", "analytics:export",
        "models:read", "audit:read", "sources:read", "users:read",
        "facilities:read", "facilities:write", "teams:read", "teams:write", "quality:read",
        "satellite:read", "satellite:verify", "notifications:read", "notifications:send",
        "replay:read", "runout:read",
    }),
    Role.DISTRICT_ADMIN: frozenset({
        "risk:read", "zone:read", "weather:read", "roads:read", "roads:write", "infra:read",
        "incidents:read", "reports:read", "reports:create", "reports:verify",
        "alerts:read", "alerts:prepare", "alerts:approve", "alerts:cancel",
        "response:read", "response:write", "scenarios:run", "analytics:read", "analytics:export",
        "models:read", "audit:read", "users:read",
        "facilities:read", "facilities:write", "teams:read", "teams:write", "quality:read",
        "satellite:read", "satellite:verify", "notifications:read", "notifications:send",
        "replay:read", "runout:read",
    }),
    Role.ANALYST: frozenset({
        "risk:read", "risk:recalculate", "zone:read", "weather:read", "roads:read", "infra:read",
        "incidents:read", "reports:read", "reports:create", "reports:verify",
        "alerts:read", "alerts:prepare", "response:read", "scenarios:run",
        "analytics:read", "analytics:export", "models:read", "sources:read", "audit:read",
        "facilities:read", "teams:read", "quality:read", "satellite:read", "notifications:read",
        "replay:read", "runout:read",
    }),
    Role.FIELD_OFFICER: frozenset({
        "risk:read", "zone:read", "weather:read", "roads:read", "roads:write", "infra:read",
        "incidents:read", "reports:read", "reports:create", "response:read", "response:write",
        "facilities:read", "teams:read", "quality:read", "replay:read", "runout:read",
    }),
    Role.CITIZEN: frozenset({
        "reports:create", "reports:read:own", "risk:read:public",
        "facilities:read", "alerts:read", "weather:read", "roads:read",
    }),
    Role.RESEARCHER: frozenset({
        "risk:read", "zone:read", "weather:read", "analytics:read", "models:read",
        "reports:read:aggregate", "quality:read", "replay:read", "runout:read",
    }),
}


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def can(role: str, permission: str) -> bool:
    return permission in permissions_for(role)


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    WATCH = "WATCH"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# Prototype starting thresholds (0-100 hazard index). Not validated operational cut-offs.
RISK_THRESHOLDS: dict[str, float] = {"WATCH": 30.0, "WARNING": 60.0, "CRITICAL": 80.0}


def risk_level_for(index: float) -> RiskLevel:
    if index >= RISK_THRESHOLDS["CRITICAL"]:
        return RiskLevel.CRITICAL
    if index >= RISK_THRESHOLDS["WARNING"]:
        return RiskLevel.WARNING
    if index >= RISK_THRESHOLDS["WATCH"]:
        return RiskLevel.WATCH
    return RiskLevel.SAFE


RISK_RANK = {RiskLevel.SAFE: 0, RiskLevel.WATCH: 1, RiskLevel.WARNING: 2, RiskLevel.CRITICAL: 3}


class PriorityLevel(StrEnum):
    P1 = "P1"  # IMMEDIATE
    P2 = "P2"  # URGENT
    P3 = "P3"  # MONITOR
    P4 = "P4"  # ROUTINE


PRIORITY_LABELS = {
    PriorityLevel.P1: "IMMEDIATE",
    PriorityLevel.P2: "URGENT",
    PriorityLevel.P3: "MONITOR",
    PriorityLevel.P4: "ROUTINE",
}


def priority_level_for(score: float) -> PriorityLevel:
    if score >= 75:
        return PriorityLevel.P1
    if score >= 55:
        return PriorityLevel.P2
    if score >= 35:
        return PriorityLevel.P3
    return PriorityLevel.P4


class DataState(StrEnum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    SIMULATED = "SIMULATED"


class CoverageLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReportStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AlertStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELIVERED = "DELIVERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    ALL_CLEAR = "ALL_CLEAR"


class RoadStatus(StrEnum):
    OPEN = "OPEN"
    RESTRICTED = "RESTRICTED"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"


class RoadStatusSource(StrEnum):
    MODEL_ESTIMATED = "MODEL_ESTIMATED"
    OFFICER_VERIFIED = "OFFICER_VERIFIED"
    OFFICIAL_CLOSURE = "OFFICIAL_CLOSURE"


class AssignmentStatus(StrEnum):
    DETECTED = "DETECTED"
    REVIEWED = "REVIEWED"
    ASSIGNED = "ASSIGNED"
    INSPECTED = "INSPECTED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


ASSIGNMENT_FLOW: dict[str, tuple[str, ...]] = {
    AssignmentStatus.DETECTED: (AssignmentStatus.REVIEWED, AssignmentStatus.ASSIGNED),
    AssignmentStatus.REVIEWED: (AssignmentStatus.ASSIGNED, AssignmentStatus.RESOLVED),
    AssignmentStatus.ASSIGNED: (AssignmentStatus.INSPECTED, AssignmentStatus.REVIEWED, AssignmentStatus.RESOLVED),
    AssignmentStatus.INSPECTED: (AssignmentStatus.RESOLVED,),
    AssignmentStatus.RESOLVED: (AssignmentStatus.REOPENED,),
    AssignmentStatus.REOPENED: (AssignmentStatus.ASSIGNED, AssignmentStatus.INSPECTED, AssignmentStatus.RESOLVED),
}


class HazardType(StrEnum):
    GROUND_CRACK = "GROUND_CRACK"
    SLOPE_MOVEMENT = "SLOPE_MOVEMENT"
    ROCKFALL = "ROCKFALL"
    ROAD_BLOCKAGE = "ROAD_BLOCKAGE"
    DEBRIS_FLOW = "DEBRIS_FLOW"
    SUBSIDENCE = "SUBSIDENCE"
    OTHER = "OTHER"


class ScenarioStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


SAFETY_DISCLAIMER = (
    "BHUSHAKTI AI provides decision support only. Hazard scores are prototype, "
    "uncalibrated model outputs, not official warnings or predictions of a specific landslide. "
    "Always follow instructions from the National Disaster Management Authority and your district administration."
)

DISCLAIMER_SHORT = "Decision support only — not an official warning."

ALERT_DISCLAIMER = (
    "Issued by the competent authority on the basis of BHUSHAKTI AI decision support. "
    "Hazard scores are uncalibrated prototype model outputs and may be wrong. "
    "This message does not guarantee that a landslide will or will not occur."
)


class FacilityType(StrEnum):
    SHELTER = "SHELTER"
    HOSPITAL = "HOSPITAL"
    HEALTH_CENTRE = "HEALTH_CENTRE"
    SCHOOL_SHELTER = "SCHOOL_SHELTER"
    ASSEMBLY_POINT = "ASSEMBLY_POINT"
    FIRE_RESCUE = "FIRE_RESCUE"
    RELIEF_CAMP = "RELIEF_CAMP"


class FacilityStatus(StrEnum):
    OPERATIONAL = "OPERATIONAL"
    STANDBY = "STANDBY"
    AT_CAPACITY = "AT_CAPACITY"
    INACCESSIBLE = "INACCESSIBLE"
    CLOSED = "CLOSED"


class TeamSpecialization(StrEnum):
    GEOTECHNICAL_ASSESSMENT = "GEOTECHNICAL_ASSESSMENT"
    SEARCH_AND_RESCUE = "SEARCH_AND_RESCUE"
    DRONE_RECONNAISSANCE = "DRONE_RECONNAISSANCE"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    EVACUATION_SUPPORT = "EVACUATION_SUPPORT"


class TeamStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    ON_SITE = "ON_SITE"
    RESTING = "RESTING"
    OFF_DUTY = "OFF_DUTY"


class DataQualityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    GOOD = "GOOD"
    WARNING = "WARNING"
    INVALID = "INVALID"
    OUTDATED = "OUTDATED"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class NotificationChannel(StrEnum):
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    CAP_RSS = "CAP_RSS"


class SatelliteVerificationStatus(StrEnum):
    UNVERIFIED_CANDIDATE = "UNVERIFIED_CANDIDATE"
    VERIFIED_LANDSLIDE = "VERIFIED_LANDSLIDE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INVESTIGATION_REQUIRED = "INVESTIGATION_REQUIRED"


class RunoutHazardClass(StrEnum):
    EXTREME = "EXTREME"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"

