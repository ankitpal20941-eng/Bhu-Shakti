"""Versioned schema migration 002 — enhancements schema + operational indexes."""

from __future__ import annotations

VERSION = "002_enhancements"

STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS ix_fac_district ON emergency_facilities (district_code, kind)",
    "CREATE INDEX IF NOT EXISTS ix_team_district ON field_teams (district_code, status)",
    "CREATE INDEX IF NOT EXISTS ix_timeline_zone ON early_warning_timeline_events (zone_id, occurred_at)",
    "CREATE INDEX IF NOT EXISTS ix_quality_source ON data_quality_reports (source_id, detected_at)",
    "CREATE INDEX IF NOT EXISTS ix_notif_alert ON notification_logs (alert_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_sat_district ON satellite_change_detections (district_code, detection_date)",
    "CREATE INDEX IF NOT EXISTS ix_impact_zone ON impact_assessments (zone_id, computed_at)",
    "CREATE INDEX IF NOT EXISTS ix_runout_zone ON landslide_runout_zones (zone_id, runout_hazard_class)",
    "CREATE INDEX IF NOT EXISTS ix_hist_district ON historical_event_records (district_code, event_date)",
)


def upgrade(conn) -> None:
    from app.models import Base

    Base.metadata.create_all(bind=conn)
    for statement in STATEMENTS:
        conn.exec_driver_sql(statement)
