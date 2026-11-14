"""Versioned schema migration 001 — initial schema + operational indexes.

Uses SQLAlchemy DDL so the same migration runs on the SQLite development
fallback and on PostgreSQL/PostGIS (where ``db/postgis_schema.sql`` adds native
geometry columns, GiST indexes and constraints).
"""

from __future__ import annotations

VERSION = "001_initial"

STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS ix_reports_status_created ON reports (status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_zone_status ON alerts (zone_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_assessment_run_zone ON risk_assessments (run_id, zone_id)",
    "CREATE INDEX IF NOT EXISTS ix_audit_action_at ON audit_logs (action, at)",
    "CREATE INDEX IF NOT EXISTS ix_assignment_zone_status ON response_assignments (zone_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_ingestion_source_time ON ingestion_runs (source_id, started_at)",
)


def upgrade(conn) -> None:
    from app.models import Base

    Base.metadata.create_all(bind=conn)
    for statement in STATEMENTS:
        conn.exec_driver_sql(statement)
