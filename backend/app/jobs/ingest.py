"""CLI: ingest weather and/or recompute risk.

    python -m app.jobs.ingest --weather
    python -m app.jobs.ingest --risk
    python -m app.jobs.ingest --all --mode simulated
"""

from __future__ import annotations

import argparse
import json
import logging

from sqlalchemy import select

from ..db import SessionLocal, run_migrations
from ..models import District
from ..services.ingestion import ingest_weather
from ..services.risk import recalculate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="BHUSHAKTI AI ingestion / risk jobs")
    parser.add_argument("--weather", action="store_true")
    parser.add_argument("--risk", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--mode", default=None, choices=["auto", "live", "simulated"])
    args = parser.parse_args()
    run_migrations()
    with SessionLocal() as db:
        districts = list(db.execute(select(District)).scalars())
        output: dict = {"districts": len(districts)}
        if args.weather or args.all:
            output["weather"] = ingest_weather(db, districts=districts, mode=args.mode,
                                               request_id="cli", actor_email="cli")
        if args.risk or args.all:
            output["risk"] = recalculate(db, district_codes=[d.code for d in districts], actor=None,
                                         request_id="cli", reason="CLI recalculation")
        print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
