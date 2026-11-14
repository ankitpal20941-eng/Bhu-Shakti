"""Environment-driven configuration.

Secrets never live in source. In development a random key is generated once and
persisted to ``backend/.dev_secret`` (git-ignored). Production must supply
``BHUSHAKTI_SECRET_KEY`` through the environment/secret manager.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
STORAGE_DIR = BACKEND_DIR / "storage"


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (no external dependency). Existing env wins."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _dev_secret() -> str:
    path = BACKEND_DIR / ".dev_secret"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path.read_text(encoding="utf-8").strip()


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


_load_dotenv(BACKEND_DIR / ".env")

ENVIRONMENT = os.environ.get("BHUSHAKTI_ENV", "demo").strip().lower()
# Production must never display seeded demonstration data.
DEMO_MODE = _bool("BHUSHAKTI_DEMO_MODE", ENVIRONMENT != "production") and ENVIRONMENT != "production"


@dataclass(frozen=True)
class Settings:
    app_name: str = "BHUSHAKTI AI"
    app_version: str = "0.9.0"
    environment: str = ENVIRONMENT
    demo_mode: bool = DEMO_MODE
    secret_key: str = field(default_factory=lambda: os.environ.get("BHUSHAKTI_SECRET_KEY") or _dev_secret())
    session_cookie: str = "bs_session"
    session_ttl_minutes: int = _int("BHUSHAKTI_SESSION_TTL_MIN", 720)
    database_url: str = os.environ.get("BHUSHAKTI_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'bhushakti.db').as_posix()}")
    storage_dir: Path = STORAGE_DIR
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.environ.get(
            "BHUSHAKTI_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        ).split(",") if o.strip()
    )
    # Weather / terrain ingestion
    # auto|live|simulated. DEMO defaults to simulated rainfall so the rainy-season
    # workflow can be exercised; every value is labelled SIMULATED in the UI.
    weather_mode: str = os.environ.get(
        "BHUSHAKTI_WEATHER_MODE", "simulated" if DEMO_MODE else "live"
    ).strip().lower()
    demo_rainfall: str = os.environ.get("BHUSHAKTI_DEMO_RAINFALL", "replay").strip().lower()  # replay|live
    open_meteo_base: str = os.environ.get("BHUSHAKTI_OPEN_METEO_BASE", "https://api.open-meteo.com/v1")
    ingestion_enabled: bool = _bool("BHUSHAKTI_INGESTION_ENABLED", True)
    ingestion_on_startup: bool = _bool("BHUSHAKTI_INGESTION_ON_STARTUP", True)
    ingestion_timeout_s: float = float(os.environ.get("BHUSHAKTI_INGESTION_TIMEOUT_S", "25"))
    # Safety / policy defaults
    seed_demo: bool = _bool("BHUSHAKTI_SEED_DEMO", DEMO_MODE)
    max_upload_bytes: int = _int("BHUSHAKTI_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    max_uploads_per_report: int = _int("BHUSHAKTI_MAX_UPLOADS_PER_REPORT", 3)
    alert_min_duration_minutes: int = _int("BHUSHAKTI_ALERT_MIN_DURATION_MIN", 30)
    alert_hysteresis_points: float = float(os.environ.get("BHUSHAKTI_ALERT_HYSTERESIS_POINTS", "5"))
    rate_limit_login_per_min: int = _int("BHUSHAKTI_RATE_LOGIN", 10)
    rate_limit_write_per_min: int = _int("BHUSHAKTI_RATE_WRITE", 60)
    active_model_version: str = os.environ.get("BHUSHAKTI_MODEL_VERSION", "suscept-v0.1+trigger-v0.1")
    log_level: str = os.environ.get("BHUSHAKTI_LOG_LEVEL", "INFO")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
