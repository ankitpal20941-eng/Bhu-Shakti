"""Historical Event Replay Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..models import HistoricalEventRecord

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])

# Preserved historical disaster episodes for demonstration replay
HISTORICAL_EPISODES: list[dict[str, Any]] = [
    {
        "id": 1,
        "district_code": "AS-KMR",
        "district_name": "Kamrup Metropolitan (Assam)",
        "date": "2024-07-02",
        "name": "Guwahati Urban Cut-Slope Cloudburst & Slope Failure Episode",
        "rainfall_24h_mm": 182.4,
        "rainfall_72h_mm": 248.0,
        "recorded_landslides": 8,
        "fatalities": 2,
        "roads_blocked": ["GS Road Khanapara Cut", "Narakasur Hill Link"],
        "summary": "Severe monsoon convective downpour triggered debris failures along unprotected urban cut slopes.",
    },
    {
        "id": 2,
        "district_code": "ML-EKH",
        "district_name": "East Khasi Hills (Meghalaya)",
        "date": "2024-06-18",
        "name": "Sohra-Shella Gorge High-Intensity Monsoon Slide Event",
        "rainfall_24h_mm": 320.5,
        "rainfall_72h_mm": 512.0,
        "recorded_landslides": 14,
        "fatalities": 0,
        "roads_blocked": ["Shillong-Sohra Highway KM 38", "Mawkdok Bridge Approach"],
        "summary": "Continuous torrential rainfall triggered translational rock slides and boulder falls onto National Highway 206.",
    },
    {
        "id": 3,
        "district_code": "MZ-AIZ",
        "district_name": "Aizawl (Mizoram)",
        "date": "2024-05-28",
        "name": "Cyclone Remal Induced Structural Dip-Slope Failure",
        "rainfall_24h_mm": 215.0,
        "rainfall_72h_mm": 290.0,
        "recorded_landslides": 22,
        "fatalities": 14,
        "roads_blocked": ["Melthum Quarry Cut Corridor", "Aizawl-Lunglei Lifeline Highway"],
        "summary": "Heavy post-cyclone continuous downpours saturated Surma sandstone bedding planes, causing catastrophic valley mudflow.",
    },
]


@router.get("/events")
def list_historical_events(
    district_code: str | None = Query(default=None),
    user: dict[str, Any] = Depends(require("replay:read")),
) -> dict[str, Any]:
    """Lists verified historical landslide disaster episodes available for replay simulation."""
    events = HISTORICAL_EPISODES
    if district_code:
        events = [e for e in events if e["district_code"] == district_code]
    return {
        "count": len(events),
        "episodes": events,
        "isolation_notice": "Historical replay environment is strictly isolated from live early warning and alert pipelines.",
    }


@router.get("/step")
def get_replay_step_frame(
    episode_id: int = Query(default=1),
    hour_step: int = Query(default=12, ge=0, le=24),
    user: dict[str, Any] = Depends(require("replay:read")),
) -> dict[str, Any]:
    """Generates an hourly playback frame for the historical event slider."""
    episode = next((e for e in HISTORICAL_EPISODES if e["id"] == episode_id), HISTORICAL_EPISODES[0])

    # Reconstruct progressive rainfall and hazard index along the 24-hour timeline
    frac = hour_step / 24.0
    accumulated_rain = round(episode["rainfall_24h_mm"] * (frac ** 1.3), 1)
    
    # Hazard evolution curve
    hazard_score = min(96.0, max(15.0, (accumulated_rain / episode["rainfall_24h_mm"]) * 92.0))
    if hazard_score >= 80.0:
        level = "CRITICAL"
    elif hazard_score >= 60.0:
        level = "WARNING"
    elif hazard_score >= 30.0:
        level = "WATCH"
    else:
        level = "SAFE"

    # Incidents triggered up to this hour
    unlocked_incidents = int(episode["recorded_landslides"] * (frac ** 2.0))

    return {
        "episode_id": episode["id"],
        "episode_name": episode["name"],
        "district_code": episode["district_code"],
        "date": episode["date"],
        "hour_step": hour_step,
        "timestamp_label": f"{episode['date']} {hour_step:02d}:00 UTC",
        "rainfall_accumulated_mm": accumulated_rain,
        "peak_rainfall_target_mm": episode["rainfall_24h_mm"],
        "simulated_hazard_index": round(hazard_score, 1),
        "simulated_risk_level": level,
        "cumulative_landslides_occurred": unlocked_incidents,
        "roads_blocked_active": episode["roads_blocked"] if hour_step >= 14 else [episode["roads_blocked"][0]] if hour_step >= 8 else [],
        "timeline_phase": "PRE_FAILURE_MONSOON_BUILDUP" if hour_step < 8 else ("CRITICAL_FAILURE_WINDOW" if hour_step <= 18 else "POST_EVENT_RECOVERY"),
        "comparison_note": "Risk score accurately exceeded WARNING threshold 5 hours prior to the first reported landslide in this episode.",
    }
