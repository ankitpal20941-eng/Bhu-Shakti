"""Data ingestion framework.

Adapters are independent of the risk engine: replacing the weather provider is a
configuration change, not a rewrite. Every run updates the data-source registry
with real timestamps, states and structured errors. A failed live feed is never
silently replaced: the fallback is a separate SIMULATED source and the UI shows
it as such.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..engine import params as P
from ..models import DataSource, District, IngestionRun, WeatherForecast, WeatherObservation
from .events import bus
from .util import as_utc, iso

log = logging.getLogger("bhushakti.ingestion")

WEATHER_SOURCE = "open-meteo-precip"
SOIL_SOURCE = "open-meteo-soil"
TERRAIN_SOURCE = "open-meteo-dem"
SIM_SOURCE = "sim-rainfall"


@dataclass
class WeatherBundle:
    district_code: str
    observed_at: datetime
    issued_at: datetime
    rainfall_1h: float | None
    rainfall_6h: float | None
    rainfall_24h: float | None
    rainfall_72h: float | None
    soil_moisture_pct: float | None
    temperature_c: float | None
    forecasts: dict[int, float]
    source_id: str
    state: str
    notes: list[str] = field(default_factory=list)


class IngestionError(RuntimeError):
    pass


def _retry(fn, *, attempts: int = 3, base_delay: float = 0.6):
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - retried with backoff below
            last = exc
            if attempt < attempts - 1:
                delay = base_delay * (3 ** attempt) + random.uniform(0, 0.3)
                log.warning("ingestion attempt %s failed: %s (retry in %.1fs)", attempt + 1, exc, delay)
                time.sleep(delay)
    raise IngestionError(str(last) if last else "unknown ingestion failure")


class OpenMeteoWeatherAdapter:
    source_id = WEATHER_SOURCE

    def __init__(self, base: str | None = None, timeout: float | None = None) -> None:
        self.base = (base or settings.open_meteo_base).rstrip("/")
        self.timeout = timeout or settings.ingestion_timeout_s

    def fetch(self, district: District) -> WeatherBundle:
        params = {
            "latitude": district.lat,
            "longitude": district.lon,
            "hourly": "precipitation,soil_moisture_0_to_7cm,temperature_2m",
            "past_days": 4,
            "forecast_days": 3,
            "timezone": "UTC",
        }

        def _call():
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base}/forecast", params=params)
                response.raise_for_status()
                return response.json()

        payload = _retry(_call)
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        precip = hourly.get("precipitation") or []
        soil = hourly.get("soil_moisture_0_to_7cm") or []
        temp = hourly.get("temperature_2m") or []
        if len(times) < 24 or not precip:
            raise IngestionError("Open-Meteo response missing hourly precipitation series")

        parsed = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in times]
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        index = max((i for i, t in enumerate(parsed) if t <= now), default=len(parsed) - 1)

        def total(hours: int) -> float | None:
            start = index - hours + 1
            if start < 0:
                return None
            window = precip[start:index + 1]
            if any(v is None for v in window):
                return None
            return round(float(sum(window)), 2)

        def forecast_sum(hours: int) -> float | None:
            start = index + 1
            end = start + hours
            if end > len(precip):
                return None
            window = precip[start:end]
            if any(v is None for v in window):
                return None
            return round(float(sum(window)), 2)

        forecasts: dict[int, float] = {}
        for horizon in P.FORECAST_HORIZONS:
            value = forecast_sum(horizon)
            if value is not None:
                forecasts[horizon] = value

        soil_value = soil[index] if index < len(soil) and soil[index] is not None else None
        return WeatherBundle(
            district_code=district.code,
            observed_at=parsed[index],
            issued_at=now,
            rainfall_1h=total(1),
            rainfall_6h=total(6),
            rainfall_24h=total(24),
            rainfall_72h=total(72),
            soil_moisture_pct=round(float(soil_value) * 100.0, 2) if soil_value is not None else None,
            temperature_c=(float(temp[index]) if index < len(temp) and temp[index] is not None else None),
            forecasts=forecasts,
            source_id=self.source_id,
            state="LIVE",
            notes=["Hourly precipitation and 0-7 cm soil moisture from Open-Meteo (model grid point nearest the district centre)."],
        )


class SimulatedWeatherAdapter:
    """Explicitly simulated fallback. Only ever surfaced with state=SIMULATED."""

    source_id = SIM_SOURCE

    def fetch(self, district: District) -> WeatherBundle:
        now = datetime.now(timezone.utc)
        seed = hashlib.sha256(f"{district.code}:{now.date().isoformat()}".encode()).hexdigest()
        rng = random.Random(seed)
        # Demonstration monsoon event: values chosen so the rainy-season workflow
        # (watch/warning confirmation, approval, response) can be exercised in DEMO.
        rain24 = round(rng.uniform(140, 260), 1)
        rain6 = round(rain24 * rng.uniform(0.35, 0.55), 1)
        rain1 = round(rain24 * rng.uniform(0.08, 0.16), 1)
        rain72 = round(rain24 * rng.uniform(1.3, 1.8), 1)
        soil = round(rng.uniform(38, 58), 1)
        forecasts = {h: round(rain24 * rng.uniform(0.35, 0.9) * (h / 24.0), 1) for h in P.FORECAST_HORIZONS}
        return WeatherBundle(
            district_code=district.code,
            observed_at=now,
            issued_at=now,
            rainfall_1h=rain1,
            rainfall_6h=rain6,
            rainfall_24h=rain24,
            rainfall_72h=rain72,
            soil_moisture_pct=soil,
            temperature_c=round(rng.uniform(18, 26), 1),
            forecasts=forecasts,
            source_id=self.source_id,
            state="SIMULATED",
            notes=[
                "SIMULATED demonstration rainfall (monsoon event replay). This is not an observation.",
                "Assessments built on this input are labelled SIMULATED throughout the interface.",
            ],
        )


class OpenMeteoElevationAdapter:
    """DEM sampling via Open-Meteo's elevation endpoint (Copernicus DEM GLO-90)."""

    source_id = TERRAIN_SOURCE
    chunk = 100

    def __init__(self, base: str | None = None, timeout: float | None = None) -> None:
        self.base = (base or settings.open_meteo_base).rstrip("/")
        self.timeout = timeout or settings.ingestion_timeout_s

    def fetch(self, coords: list[tuple[float, float]]) -> list[float | None]:
        out: list[float | None] = []
        for i in range(0, len(coords), self.chunk):
            batch = coords[i:i + self.chunk]
            params = {
                "latitude": ",".join(f"{lat:.5f}" for lat, _ in batch),
                "longitude": ",".join(f"{lon:.5f}" for _, lon in batch),
            }

            def _call(batch=params):
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(f"{self.base}/elevation", params=batch)
                    response.raise_for_status()
                    return response.json()

            payload = _retry(_call, attempts=2)
            elevations = payload.get("elevation") or []
            out.extend(float(v) if v is not None else None for v in elevations)
        if len(out) != len(coords):
            log.warning("elevation response length mismatch: %s vs %s", len(out), len(coords))
            out.extend([None] * (len(coords) - len(out)))
        return out[:len(coords)]


# ---------------------------------------------------------------- persistence
def _upsert_source_state(
    db: Session,
    source_id: str,
    *,
    state: str,
    success: bool,
    error: str | None = None,
    request_id: str = "",
    records: int = 0,
    started: datetime | None = None,
    message: str = "",
) -> None:
    source = db.get(DataSource, source_id)
    if source is None:
        return
    now = datetime.now(timezone.utc)
    source.last_attempt_at = now
    source.state = state
    if success:
        source.last_success_at = now
        source.last_error = None
    elif error:
        source.last_error = error[:2000]
    db.add(IngestionRun(
        source_id=source_id,
        started_at=started or now,
        finished_at=now,
        status="SUCCESS" if success else "FAILED",
        records=records,
        message=message or (error or ""),
        request_id=request_id,
        duration_ms=int((now - (started or now)).total_seconds() * 1000),
    ))


def persist_bundle(db: Session, bundle: WeatherBundle) -> int:
    existing = db.execute(
        select(WeatherObservation).where(
            WeatherObservation.district_code == bundle.district_code,
            WeatherObservation.source_id == bundle.source_id,
            WeatherObservation.observed_at == bundle.observed_at,
        )
    ).scalars().first()
    if existing is None:
        db.add(WeatherObservation(
            district_code=bundle.district_code,
            observed_at=bundle.observed_at,
            rainfall_1h=bundle.rainfall_1h,
            rainfall_6h=bundle.rainfall_6h,
            rainfall_24h=bundle.rainfall_24h,
            rainfall_72h=bundle.rainfall_72h,
            soil_moisture_pct=bundle.soil_moisture_pct,
            temperature_c=bundle.temperature_c,
            source_id=bundle.source_id,
            source_state=bundle.state,
        ))
    db.execute(delete(WeatherForecast).where(
        WeatherForecast.district_code == bundle.district_code,
        WeatherForecast.source_id == bundle.source_id,
    ))
    for horizon, mm in bundle.forecasts.items():
        db.add(WeatherForecast(
            district_code=bundle.district_code,
            issued_at=bundle.issued_at,
            target_time=bundle.issued_at + timedelta(hours=horizon),
            horizon_h=horizon,
            rainfall_mm=float(mm),
            source_id=bundle.source_id,
            source_state=bundle.state,
        ))
    return 1 + len(bundle.forecasts)


def ingest_weather(
    db: Session,
    *,
    districts: Iterable[District],
    mode: str | None = None,
    request_id: str = "",
    actor_email: str = "system",
) -> dict[str, Any]:
    mode = (mode or settings.weather_mode or "auto").lower()
    districts = list(districts)
    adapter: Any
    if mode == "simulated" or not settings.ingestion_enabled:
        adapter = SimulatedWeatherAdapter()
        mode = "simulated"
    else:
        adapter = OpenMeteoWeatherAdapter()

    results: list[dict[str, Any]] = []
    degraded = False
    for district in districts:
        started = datetime.now(timezone.utc)
        try:
            bundle = adapter.fetch(district)
            records = persist_bundle(db, bundle)
            _upsert_source_state(
                db, bundle.source_id, state=bundle.state, success=True,
                request_id=request_id, records=records, started=started,
                message="; ".join(bundle.notes),
            )
            if bundle.state == "LIVE" and bundle.soil_moisture_pct is not None:
                _upsert_source_state(db, SOIL_SOURCE, state="LIVE", success=True,
                                     request_id=request_id, records=1, started=started,
                                     message="Soil moisture stored with the rainfall observation")
            results.append({
                "district_code": district.code,
                "source_id": bundle.source_id,
                "state": bundle.state,
                "observed_at": iso(bundle.observed_at),
                "rainfall_24h": bundle.rainfall_24h,
                "forecasts": bundle.forecasts,
            })
        except Exception as exc:  # noqa: BLE001 - recorded, then fallback
            degraded = True
            message = f"{type(exc).__name__}: {exc}"
            log.warning("live weather ingestion failed for %s: %s", district.code, message)
            _upsert_source_state(db, WEATHER_SOURCE, state="DEGRADED", success=False,
                                 error=message, request_id=request_id, started=started)
            if mode == "live":
                results.append({"district_code": district.code, "source_id": WEATHER_SOURCE,
                                "state": "UNAVAILABLE", "error": message})
                continue
            fallback = SimulatedWeatherAdapter().fetch(district)
            records = persist_bundle(db, fallback)
            _upsert_source_state(db, SIM_SOURCE, state="SIMULATED", success=True,
                                 request_id=request_id, records=records, started=started,
                                 message="Fallback demonstration rainfall (live feed failed)")
            results.append({
                "district_code": district.code,
                "source_id": fallback.source_id,
                "state": "SIMULATED",
                "observed_at": iso(fallback.observed_at),
                "rainfall_24h": fallback.rainfall_24h,
                "forecasts": fallback.forecasts,
                "warning": "Live feed failed; simulated rainfall used and labelled SIMULATED.",
            })
    db.commit()
    by_district = {r["district_code"]: r for r in results}
    if degraded:
        bus.publish("feed.degraded", {"sources": [WEATHER_SOURCE], "details": results})
    return {
        "mode": mode,
        "districts": len(districts),
        "results": results,
        "by_district": by_district,
        "degraded": degraded,
        "activated_by": actor_email,
    }


def district_weather_state(db: Session, district_code: str) -> dict[str, Any]:
    from .risk import effective_weather_state, latest_weather  # local import to avoid cycles

    weather = latest_weather(db, district_code)
    if weather is None:
        return {"state": "UNAVAILABLE", "observed_at": None, "source_id": None, "age_minutes": None}
    source = db.get(DataSource, weather.source_id)
    state = effective_weather_state(source, as_utc(weather.observed_at), datetime.now(timezone.utc))
    return {
        "state": state.value,
        "observed_at": iso(weather.observed_at),
        "source_id": weather.source_id,
        "age_minutes": None,
        "rainfall_24h": weather.rainfall_24h,
        "soil_moisture_pct": weather.soil_moisture_pct,
    }
