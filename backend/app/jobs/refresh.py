"""Periodic refresh: ingest weather, then recompute risk and alert candidates.

Runs in a daemon thread so the API stays responsive. Every run opens its own
session; failures are logged and recorded in the source registry, never hidden.
"""

from __future__ import annotations

import logging
import os
import threading
import time

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models import District
from ..services.ingestion import ingest_weather
from ..services.risk import recalculate

log = logging.getLogger("bhushakti.refresh")

REFRESH_MINUTES = int(os.environ.get("BHUSHAKTI_REFRESH_MIN", "15"))


def refresh_cycle(reason: str = "Scheduled refresh") -> dict | None:
    with SessionLocal() as db:
        districts = list(db.execute(select(District)).scalars())
        if not districts:
            return None
        ingestion = ingest_weather(db, districts=districts, request_id="scheduler", actor_email="scheduler")
        summary = recalculate(db, district_codes=[d.code for d in districts], actor=None,
                              request_id="scheduler", reason=reason)
        log.info("refresh complete: %s zones, %s candidates, degraded=%s",
                 summary.get("zones_assessed"), summary.get("alert_candidates_created"),
                 ingestion.get("degraded"))
        return {"ingestion": ingestion, "risk": summary}


def start_scheduler(stop_event: threading.Event) -> threading.Thread:
    def loop() -> None:
        # Small initial delay so startup (migrations/seed) completes first.
        if stop_event.wait(10):
            return
        while not stop_event.is_set():
            try:
                refresh_cycle()
            except Exception:  # noqa: BLE001
                log.exception("scheduled refresh failed")
            stop_event.wait(REFRESH_MINUTES * 60)

    thread = threading.Thread(target=loop, name="bhushakti-refresh", daemon=True)
    thread.start()
    return thread
