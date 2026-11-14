# ADR 0006 — In-process scheduler instead of Celery/Redis

**Status:** accepted · **Date:** November 2026

## Context

The brief lists Celery, Redis and MLflow. The prototype is a single-node application with a
handful of periodic tasks (ingest weather, recalculate risk, expire alerts). Running Redis and a
worker fleet for that would add two services to every reviewer's machine without improving any
behaviour the product demonstrates.

## Decision

- Run the scheduler inside the FastAPI lifespan, guarded so it starts once per process.
- Document explicitly that the service must run with `--workers 1`, or the scheduler must be moved
  to its own process before horizontal scaling.
- Keep the task functions (`jobs/ingest.py`, `jobs/refresh.py`) importable so a Celery beat/worker
  can call them later without rewriting business logic.

## Consequences

- One process, one command, no broker to operate.
- No distributed locking, retry queue, dead-letter handling, or task observability; a failed run is
  recorded in `ingestion_runs` and visible on Data Health.
- Scaling out requires moving the scheduler first — a documented deployment constraint, not a
  hidden behaviour.
