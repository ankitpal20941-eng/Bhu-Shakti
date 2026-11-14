# ADR 0005 — SQLite for development, PostgreSQL/PostGIS for production

**Status:** accepted · **Date:** November 2026

## Context

The brief asks for PostgreSQL/PostGIS. The development machine had Python 3.14 but no PostgreSQL
server, and a reviewer must be able to run the system with one command. Installing and operating a
database server would have blocked delivery of the actual product.

## Decision

- Use SQLAlchemy 2 with portable column types; default to SQLite at `backend/data/bhushakti.db`.
- Ship a versioned, forward-only migration runner (`app/db.py`, `backend/migrations`) that works on
  both engines.
- Keep geometry as GeoJSON in JSON columns plus a bbox for filtering, so nothing in the API depends
  on PostGIS.
- Document the PostGIS migration path: install `psycopg`, set `BHUSHAKTI_DATABASE_URL`, add a
  migration that converts geometry columns and backfills, then add GiST indexes.

## Consequences

- The prototype runs anywhere with Python, and tests execute in seconds against a real SQL database.
- Spatial queries are currently haversine-in-Python; fine for 116 units, not for a state.
- JSON geometry is larger on the wire than vector tiles and has no server-side spatial index yet.
- Production performance must be re-measured on PostgreSQL; no figures are claimed here.
