"""Normalized relational schema (SQLite dev fallback; PostgreSQL/PostGIS in production).

Geometries are stored as GeoJSON documents plus a bounding box for indexed
pre-filtering. ``db/postgis_schema.sql`` documents the equivalent PostGIS layout
and the migration path to native geometry columns, GiST indexes and vector tiles.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class RoleRow(Base):
    __tablename__ = "roles"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(400), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class District(Base):
    __tablename__ = "districts"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    state_code: Mapped[str] = mapped_column(String(8), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    boundary_source: Mapped[str] = mapped_column(String(200), nullable=False)
    boundary_note: Mapped[str] = mapped_column(Text, nullable=False)
    population_estimate: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserScope(Base):
    __tablename__ = "user_scopes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("user_id", "district_code", name="uq_user_scope"),)


class SpatialUnit(Base):
    """Prediction unit. Grid cells are the practical fallback where slope-unit
    delineation is unavailable; each unit carries explicit provenance."""

    __tablename__ = "spatial_units"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(24), default="grid_cell", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    bbox_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    slope_deg: Mapped[float | None] = mapped_column(Float)
    aspect_deg: Mapped[float | None] = mapped_column(Float)
    curvature: Mapped[float | None] = mapped_column(Float)
    terrain_ruggedness: Mapped[float | None] = mapped_column(Float)
    twi: Mapped[float | None] = mapped_column(Float)
    landcover: Mapped[str | None] = mapped_column(String(60))
    geology: Mapped[str | None] = mapped_column(String(60))
    road_cut_proximity_m: Mapped[float | None] = mapped_column(Float)
    terrain_source: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    landcover_source: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    geology_source: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hazard_index: Mapped[float] = mapped_column(Float, nullable=False)
    hazard_level: Mapped[str] = mapped_column(String(16), nullable=False)
    hazard_probability: Mapped[float | None] = mapped_column(Float)
    probability_status: Mapped[str] = mapped_column(String(32), default="NOT_CALIBRATED", nullable=False)
    exposure_score: Mapped[float] = mapped_column(Float, nullable=False)
    vulnerability_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(4), nullable=False)
    coverage_level: Mapped[str] = mapped_column(String(8), nullable=False)
    out_of_domain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    drivers: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    data_age_minutes: Mapped[int | None] = mapped_column(Integer)
    weather_source_state: Mapped[str] = mapped_column(String(16), default="UNAVAILABLE", nullable=False)
    is_scenario: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    scenario_run_id: Mapped[int | None] = mapped_column(ForeignKey("scenario_runs.id", ondelete="CASCADE"), index=True)
    __table_args__ = (
        UniqueConstraint("zone_id", "run_id", name="uq_assessment_zone_run"),
        Index("ix_assessment_zone_time", "zone_id", "computed_at"),
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    rainfall_1h: Mapped[float | None] = mapped_column(Float)
    rainfall_6h: Mapped[float | None] = mapped_column(Float)
    rainfall_24h: Mapped[float | None] = mapped_column(Float)
    rainfall_72h: Mapped[float | None] = mapped_column(Float)
    soil_moisture_pct: Mapped[float | None] = mapped_column(Float)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[str] = mapped_column(String(60), nullable=False)
    source_state: Mapped[str] = mapped_column(String(16), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("district_code", "observed_at", "source_id", name="uq_weather_obs"),)


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    horizon_h: Mapped[int] = mapped_column(Integer, nullable=False)
    rainfall_mm: Mapped[float] = mapped_column(Float, nullable=False)
    source_id: Mapped[str] = mapped_column(String(60), nullable=False)
    source_state: Mapped[str] = mapped_column(String(16), nullable=False)
    __table_args__ = (UniqueConstraint("district_code", "target_time", "horizon_h", "source_id", name="uq_weather_fc"),)


class SoilMoistureRecord(Base):
    __tablename__ = "soil_moisture_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    depth_cm: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    volumetric_pct: Mapped[float] = mapped_column(Float, nullable=False)
    source_id: Mapped[str] = mapped_column(String(60), nullable=False)
    source_state: Mapped[str] = mapped_column(String(16), nullable=False)


class Sensor(Base):
    __tablename__ = "sensors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_units.id", ondelete="SET NULL"))
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="UNAVAILABLE", nullable=False)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)


class LandslideIncident(Base):
    __tablename__ = "landslide_incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_units.id", ondelete="SET NULL"), index=True)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_uncertainty_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    location_accuracy_m: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (Index("ix_incident_district_date", "district_code", "occurred_on"),)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_units.id", ondelete="SET NULL"), index=True)
    district_code: Mapped[str | None] = mapped_column(ForeignKey("districts.code"), index=True)
    hazard_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING_VERIFICATION", nullable=False, index=True)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reporter_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reporter_name: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(160))
    consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_adjustment_applied: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(80))
    sync_source: Mapped[str] = mapped_column(String(24), default="online", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    media: Mapped[list["ReportMedia"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ReportMedia(Base):
    __tablename__ = "report_media"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    report: Mapped[Report] = relationship(back_populates="media")


class Road(Base):
    __tablename__ = "roads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    road_class: Mapped[str] = mapped_column(String(40), nullable=False)
    district_codes: Mapped[list] = mapped_column(JSON, nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    geometry_note: Mapped[str] = mapped_column(Text, default="", nullable=False)


class RoadSegment(Base):
    __tablename__ = "road_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    road_id: Mapped[int] = mapped_column(ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_units.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    status_source: Mapped[str] = mapped_column(String(24), default="MODEL_ESTIMATED", nullable=False)
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status_updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_risk_level: Mapped[str | None] = mapped_column(String(16))
    __table_args__ = (Index("ix_segment_zone", "zone_id"),)


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    capacity: Mapped[int | None] = mapped_column(Integer)
    population_estimate: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    source_state: Mapped[str] = mapped_column(String(16), default="SIMULATED", nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="CANDIDATE", nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(240), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    onset: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    threatened_assets: Mapped[list] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    template_version: Mapped[str] = mapped_column(String(40), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    hazard_index: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(4), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    is_scenario: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)


class AlertApproval(Base):
    __tablename__ = "alert_approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    template_version: Mapped[str] = mapped_column(String(40), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ResponseAssignment(Base):
    __tablename__ = "response_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    priority: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DETECTED", nullable=False, index=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_email: Mapped[str] = mapped_column(String(200), default="anonymous", nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), default="anonymous", nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request_id: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    provider: Mapped[str] = mapped_column(String(160), nullable=False)
    licence: Mapped[str] = mapped_column(String(200), nullable=False)
    attribution: Mapped[str] = mapped_column(String(300), nullable=False)
    spatial_resolution: Mapped[str] = mapped_column(String(80), nullable=False)
    temporal_resolution: Mapped[str] = mapped_column(String(80), nullable=False)
    expected_refresh_min: Mapped[int] = mapped_column(Integer, nullable=False)
    freshness_sla_min: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_source: Mapped[str | None] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(16), default="UNAVAILABLE", nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    coverage: Mapped[str] = mapped_column(String(200), default="", nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    request_id: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    features: Mapped[list] = mapped_column(JSON, nullable=False)
    training_period: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    spatial_coverage: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    validation_approach: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PROTOTYPE", nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    card: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changelog: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_versions.version"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    district_code: Mapped[str | None] = mapped_column(ForeignKey("districts.code"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    baseline_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AlertPolicy(Base):
    __tablename__ = "alert_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, nullable=False)
    hysteresis_points: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    min_duration_min: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    dedupe_window_min: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(200), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class DistrictRainfallThreshold(Base):
    __tablename__ = "district_rainfall_thresholds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), unique=True, nullable=False, index=True)
    threshold_24h_watch_mm: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_24h_warning_mm: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_24h_critical_mm: Mapped[float] = mapped_column(Float, nullable=False)
    antecedent_72h_mm: Mapped[float] = mapped_column(Float, nullable=False)
    intensity_alpha: Mapped[float] = mapped_column(Float, default=14.5, nullable=False)
    intensity_beta: Mapped[float] = mapped_column(Float, default=0.38, nullable=False)
    calibrated_by: Mapped[str] = mapped_column(String(160), default="Regional Geotechnical Panel", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(40), default="LOCALLY_CALIBRATED", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EmergencyFacility(Base):
    __tablename__ = "emergency_facilities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # FacilityType
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    contact_officer: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    power_backup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    water_supply: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    medical_supplies: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPERATIONAL", nullable=False)
    verified_by_authority: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class FieldTeam(Base):
    __tablename__ = "field_teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    team_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    leader_name: Mapped[str] = mapped_column(String(120), nullable=False)
    leader_phone: Mapped[str] = mapped_column(String(60), nullable=False)
    specialization: Mapped[str] = mapped_column(String(60), nullable=False)  # TeamSpecialization
    base_lat: Mapped[float] = mapped_column(Float, nullable=False)
    base_lon: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE", nullable=False)  # TeamStatus
    member_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    current_active_assignments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    equipment: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class FieldAssignmentRecommendation(Base):
    __tablename__ = "field_assignment_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("response_assignments.id", ondelete="CASCADE"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("field_teams.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[str] = mapped_column(String(4), nullable=False)
    estimated_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_transit_min: Mapped[int] = mapped_column(Integer, nullable=False)
    road_accessible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    skill_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    workload_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    overridden_by_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EarlyWarningTimelineEvent(Base):
    __tablename__ = "early_warning_timeline_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"), index=True)
    milestone: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_name: Mapped[str] = mapped_column(String(120), default="Automated Sensing Pipeline", nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    lead_time_minutes: Mapped[int | None] = mapped_column(Integer)
    effectiveness_score: Mapped[float | None] = mapped_column(Float)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # DataQualityStatus
    value: Mapped[float | None] = mapped_column(Float)
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    records_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    resolution_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # NotificationChannel
    recipient_target: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)  # DeliveryStatus
    subject: Mapped[str] = mapped_column(String(250), nullable=False)
    message_preview: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(100))
    provider_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    escalation_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SatelliteChangeDetection(Base):
    __tablename__ = "satellite_change_detections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_units.id", ondelete="SET NULL"), index=True)
    satellite_source: Mapped[str] = mapped_column(String(80), nullable=False)  # Sentinel-2, PlanetScope
    baseline_date: Mapped[date] = mapped_column(Date, nullable=False)
    detection_date: Mapped[date] = mapped_column(Date, nullable=False)
    ndvi_drop_pct: Mapped[float] = mapped_column(Float, nullable=False)
    disturbance_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    scar_lat: Mapped[float] = mapped_column(Float, nullable=False)
    scar_lon: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="UNVERIFIED_CANDIDATE", nullable=False)
    candidate_incident_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    geometry_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ImpactAssessment(Base):
    __tablename__ = "impact_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hazard_index: Mapped[float] = mapped_column(Float, nullable=False)
    exposed_population: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    affected_roads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    isolated_settlements_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_hospitals_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bridges_affected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schools_affected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alternative_routes_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    isolation_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LandslideRunoutZone(Base):
    __tablename__ = "landslide_runout_zones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("spatial_units.id", ondelete="CASCADE"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    runout_angle_deg: Mapped[float] = mapped_column(Float, nullable=False)  # Fahrböschung angle
    max_runout_length_m: Mapped[float] = mapped_column(Float, nullable=False)
    affected_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    slope_gradient_deg: Mapped[float] = mapped_column(Float, nullable=False)
    flow_direction_deg: Mapped[float] = mapped_column(Float, default=180.0, nullable=False)
    runout_hazard_class: Mapped[str] = mapped_column(String(30), default="HIGH", nullable=False)
    downslope_path_geojson: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    threatened_settlements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    threatened_roads: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HistoricalEventRecord(Base):
    __tablename__ = "historical_event_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("districts.code"), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rainfall_24h_mm: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_72h_mm: Mapped[float] = mapped_column(Float, nullable=False)
    max_hazard_index: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_landslides_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fatalities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    displaced_persons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    roads_blocked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timeline_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

