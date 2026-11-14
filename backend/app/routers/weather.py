"""Weather, forecasts, soil moisture and source attribution."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import require, user_scopes
from ..models import DataSource, District, WeatherForecast, WeatherObservation
from ..services.risk import effective_weather_state
from ..services.serializers import source_dict
from ..services.util import as_utc, iso, minutes_since

router = APIRouter(prefix="/api/v1", tags=["weather"])


@router.get("/weather")
def weather(
    db: Session = Depends(get_db),
    user=Depends(require("weather:read")),
    district_code: str | None = None,
):
    allowed = user_scopes(user)
    stmt = select(District)
    if district_code:
        if allowed is not None and district_code not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
        stmt = stmt.where(District.code == district_code)
    elif allowed is not None:
        stmt = stmt.where(District.code.in_(allowed))
    districts = list(db.execute(stmt).scalars())
    if not districts:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No districts in scope")

    now = datetime.now(timezone.utc)
    out = []
    for district in districts:
        observation = db.execute(
            select(WeatherObservation).where(WeatherObservation.district_code == district.code)
            .order_by(WeatherObservation.observed_at.desc()).limit(1)
        ).scalars().first()
        source = db.get(DataSource, observation.source_id) if observation else None
        state = effective_weather_state(source, as_utc(observation.observed_at) if observation else None, now)
        forecasts = list(db.execute(
            select(WeatherForecast).where(WeatherForecast.district_code == district.code)
            .order_by(WeatherForecast.issued_at.desc())
        ).scalars())
        latest_issued = max((as_utc(f.issued_at) for f in forecasts), default=None)
        series = sorted(
            [{"horizon_h": f.horizon_h, "rainfall_mm": f.rainfall_mm,
              "target_time": iso(f.target_time), "source_state": f.source_state}
             for f in forecasts if latest_issued and as_utc(f.issued_at) == latest_issued],
            key=lambda x: x["horizon_h"],
        )
        out.append({
            "district_code": district.code,
            "district_name": district.name,
            "state": district.state,
            "observation": None if observation is None else {
                "observed_at": iso(observation.observed_at),
                "age_minutes": minutes_since(observation.observed_at, now),
                "rainfall_1h": observation.rainfall_1h,
                "rainfall_6h": observation.rainfall_6h,
                "rainfall_24h": observation.rainfall_24h,
                "rainfall_72h": observation.rainfall_72h,
                "soil_moisture_pct": observation.soil_moisture_pct,
                "temperature_c": observation.temperature_c,
                "source_id": observation.source_id,
            },
            "source_state": state.value,
            "source": source_dict(source) if source else None,
            "forecasts": series,
            "forecast_issued_at": iso(latest_issued),
            "attribution": source.attribution if source else "No data source available",
            "notes": [
                "Rainfall values are model grid-point output for the nearest point to the district centre, not a rain-gauge observation.",
                "SIMULATED values are demonstration data and are never presented as observations.",
            ],
        })
    return {
        "districts": out,
        "weather_mode": settings.weather_mode,
        "demo_mode": settings.demo_mode,
        "generated_at": iso(now),
    }
