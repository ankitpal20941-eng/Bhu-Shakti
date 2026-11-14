"""Test configuration.

The environment is configured BEFORE importing the app so the isolated SQLite file
is used and no network ingestion runs during tests.
"""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test_bhushakti.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["BHUSHAKTI_DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["BHUSHAKTI_INGESTION_ENABLED"] = "false"
os.environ["BHUSHAKTI_SEED_DEMO"] = "false"
os.environ["BHUSHAKTI_WEATHER_MODE"] = "simulated"
os.environ["BHUSHAKTI_ENV"] = "demo"
os.environ["BHUSHAKTI_SECRET_KEY"] = "test-only-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, run_migrations  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import DEMO_PASSWORD, seed_database  # noqa: E402

DEMO_USERS = {
    "admin": "admin@bhushakti.demo",
    "state": "state.assam@bhushakti.demo",
    "district": "dc.kamrup@bhushakti.demo",
    "analyst": "analyst@bhushakti.demo",
    "field": "field.officer@bhushakti.demo",
    "citizen": "citizen@bhushakti.demo",
    "researcher": "researcher@bhushakti.demo",
}


@pytest.fixture(scope="session")
def client() -> TestClient:
    run_migrations()
    with SessionLocal() as db:
        seed_database(db, with_network=False)
        # Deterministic simulated rainfall so the full pipeline (trigger, alerts)
        # can be exercised without network access.
        from sqlalchemy import select

        from app.models import District
        from app.services.ingestion import ingest_weather
        from app.services.risk import recalculate

        districts = list(db.execute(select(District)).scalars())
        ingest_weather(db, districts=districts, mode="simulated")
        recalculate(db, district_codes=[d.code for d in districts], reason="test bootstrap")
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, role: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_USERS[role], "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture(scope="session")
def tokens(client: TestClient) -> dict[str, dict]:
    return {role: login(client, role) for role in DEMO_USERS}
