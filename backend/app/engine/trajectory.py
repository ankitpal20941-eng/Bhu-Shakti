"""Forecast trajectory: only horizons with actual forecast inputs are computed."""

from __future__ import annotations

from typing import Any

from ..domain import risk_level_for
from . import params as P
from .hazard import TriggerResult, combine_hazard, dynamic_trigger


def build_trajectory(
    *,
    static_index: float,
    rainfall_1h: float | None,
    rainfall_6h: float | None,
    rainfall_24h: float | None,
    rainfall_72h: float | None,
    soil_moisture_pct: float | None,
    month: int,
    forecasts: dict[int, float],
    forecast_issued_at: str | None,
) -> dict[str, Any]:
    """Return hazard estimates per supported horizon.

    A horizon is included only when a forecast value exists for it. Missing
    horizons are listed with an explicit reason — never filled with invented data.
    """
    points: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for horizon in P.FORECAST_HORIZONS:
        forecast_mm = forecasts.get(horizon)
        if forecast_mm is None:
            missing.append({
                "horizon_h": horizon,
                "reason": "No forecast ingested for this horizon",
            })
            continue
        trigger: TriggerResult = dynamic_trigger(
            rainfall_1h=rainfall_1h,
            rainfall_6h=rainfall_6h,
            rainfall_24h=rainfall_24h,
            rainfall_72h=rainfall_72h,
            forecast_24h=forecast_mm,
            soil_moisture_pct=soil_moisture_pct,
            month=month,
        )
        hazard, breakdown = combine_hazard(static_index, trigger.index, trigger.available)
        level = risk_level_for(hazard)
        points.append({
            "horizon_h": horizon,
            "hazard_index": hazard,
            "hazard_level": level.value,
            "trigger_index": trigger.index,
            "forecast_rainfall_mm": forecast_mm,
            "forecast_issued_at": forecast_issued_at,
            "probability_status": "NOT_CALIBRATED",
            "note": "Hazard index from forecast rainfall, not a calibrated probability.",
        })
    return {
        "points": points,
        "missing": missing,
        "supported_horizons": [p["horizon_h"] for p in points],
        "unavailable_horizons": [m["horizon_h"] for m in missing],
        "method": "Same susceptibility baseline with forecast rainfall replacing observed intensity.",
        "probability_status": "NOT_CALIBRATED",
    }
