"""BHUSHAKTI AI API application."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend root is on sys.path so 'import app...' succeeds from any execution directory
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import logging
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import settings
from .db import SessionLocal, engine, run_migrations
from .jobs.refresh import start_scheduler
from .routers import (
    admin,
    alerts,
    analytics,
    auth,
    facilities,
    impact,
    infrastructure,
    model_monitoring,
    notifications,
    public,
    quality,
    rainfall,
    replay,
    reports,
    response,
    risk,
    roads,
    runout,
    satellite,
    scenarios,
    situation_room,
    stream,
    teams,
    timeline,
    weather,
)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("bhushakti")

_stop_event = threading.Event()


def _bootstrap_data() -> None:
    from sqlalchemy import select

    from .models import District
    from .seed import seed_database

    try:
        with SessionLocal() as db:
            if db.execute(select(District)).scalars().first() is not None:
                return
            if not settings.seed_demo:
                log.warning(
                    "Database is empty and BHUSHAKTI_SEED_DEMO is disabled. "
                    "Load authoritative data before going live."
                )
                return
            log.info("seeding demonstration dataset (three pilot districts)…")
            summary = seed_database(db, with_network=settings.ingestion_enabled)
            log.info("seed complete: %s", {k: summary.get(k) for k in
                                          ("zones", "districts", "weather_ingested")})
    except Exception:  # noqa: BLE001 - startup must not crash the API
        log.exception("seeding failed; API will start with whatever data exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    _bootstrap_data()
    scheduler = None
    if settings.ingestion_enabled:
        scheduler = start_scheduler(_stop_event)
    log.info("BHUSHAKTI AI %s ready (env=%s, demo=%s)", __version__, settings.environment,
             settings.demo_mode)
    try:
        yield
    finally:
        _stop_event.set()
        if scheduler is not None:
            scheduler.join(timeout=2)


app = FastAPI(
    title="BHUSHAKTI AI",
    description=(
        "Landslide early-warning and risk-intelligence API for India's North Eastern Region. "
        "SENSE → PREDICT → EXPLAIN → PRIORITIZE → ACT. Hazard scores are uncalibrated prototype "
        "indices for decision support, not official warnings."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)


@app.middleware("http")
async def request_context_and_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - converted to a structured 500 below
        log.exception("unhandled error on %s %s (request_id=%s)", request.method, request.url.path, request_id)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Unexpected server error"},
                     "request_id": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(self), camera=(self), microphone=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)},
            "request_id": getattr(request.state, "request_id", ""),
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": [
                    {"location": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                    for e in exc.errors()
                ],
            },
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


for module in (
    auth, risk, weather, roads, infrastructure, reports, alerts, response,
    scenarios, analytics, admin, stream, public,
    situation_room, impact, rainfall, runout, timeline, model_monitoring,
    facilities, quality, notifications, replay, teams, satellite,
):
    app.include_router(module.router)


@app.get("/api/v1/health", tags=["system"])
def health():
    from sqlalchemy import text

    database_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_ok = False
    return {
        "status": "ok" if database_ok else "degraded",
        "version": __version__,
        "database": "ok" if database_ok else "unavailable",
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "model_version": settings.active_model_version,
        "probability_status": "NOT_CALIBRATED",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "BHUSHAKTI AI",
        "version": __version__,
        "docs": "/api/docs",
        "health": "/api/v1/health",
        "statement": (
            "We do not just identify where landslide risk exists. We explain why it is increasing, "
            "determine what is exposed, and help authorities decide where to act first."
        ),
    }
