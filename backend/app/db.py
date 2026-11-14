"""Database session, migration runner and SQLite development fallback."""

from __future__ import annotations

import importlib.util
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .config import DATA_DIR, STORAGE_DIR, settings

log = logging.getLogger("bhushakti.db")
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "versions"


def _make_engine() -> Engine:
    url = settings.database_url
    if url.startswith("sqlite"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = url.split("?")[0]
        for prefix in ("sqlite:////", "sqlite:///", "sqlite://"):
            if raw_path.startswith(prefix):
                file_part = raw_path[len(prefix):]
                if prefix == "sqlite:////":
                    file_part = "/" + file_part
                if file_part and file_part != ":memory:":
                    Path(file_part).parent.mkdir(parents=True, exist_ok=True)
                break
        engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

        return engine
    # PostgreSQL/PostGIS in production. Geometry columns require the PostGIS
    # extension; see db/postgis_schema.sql for the native schema.
    return create_engine(url, pool_pre_ping=True, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _applied(conn) -> set[str]:
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version VARCHAR(80) PRIMARY KEY, applied_at TIMESTAMP NOT NULL)"
    ))
    rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {r[0] for r in rows}


def run_migrations() -> list[str]:
    """Apply versioned Python migrations in filename order, once each."""
    applied: list[str] = []
    with engine.begin() as conn:
        done = _applied(conn)
        for path in sorted(MIGRATIONS_DIR.glob("*.py")):
            spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            version = getattr(module, "VERSION", path.stem)
            if version in done:
                continue
            log.info("applying migration %s", version)
            module.upgrade(conn)
            conn.execute(
                text("INSERT INTO schema_migrations (version, applied_at) VALUES (:v, :a)"),
                {"v": version, "a": datetime.now(timezone.utc).isoformat()},
            )
            applied.append(version)
    return applied
