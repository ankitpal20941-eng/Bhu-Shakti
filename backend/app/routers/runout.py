"""Landslide Runout and Impact Zone Analysis Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require
from ..engine.runout import estimate_debris_runout
from ..models import InfrastructureAsset, RiskAssessment, RoadSegment, SpatialUnit

router = APIRouter(prefix="/api/v1/runout", tags=["runout"])


class RunoutSimulationRequest(BaseModel):
    zone_id: int
    estimated_volume_m3: float = Field(default=8500.0, ge=100.0, le=500000.0)


@router.get("/zones")
def list_runout_zones(
    district_code: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("runout:read")),
) -> dict[str, Any]:
    """Retrieves high-hazard slope units with computed empirical debris runout envelopes."""
    stmt = (
        select(SpatialUnit, RiskAssessment)
        .join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
        .order_by(RiskAssessment.hazard_index.desc())
        .limit(limit)
    )
    if district_code:
        stmt = stmt.where(SpatialUnit.district_code == district_code)

    units = db.execute(stmt).all()
    results = []

    for zone, assessment in units:
        elevation = float(zone.elevation_m or 420.0)
        slope = float(zone.slope_deg or 32.0)
        aspect = float(zone.aspect_deg or 180.0)

        runout_data = estimate_debris_runout(
            start_lat=zone.centroid_lat,
            start_lon=zone.centroid_lon,
            elevation_m=elevation,
            slope_deg=slope,
            aspect_deg=aspect,
        )

        # Identify threatened assets in proximity
        assets = db.execute(
            select(InfrastructureAsset).where(InfrastructureAsset.district_code == zone.district_code)
        ).scalars().all()
        threatened_settlements = [a.name for a in assets if a.kind == "settlements"][:2]

        roads = db.execute(
            select(RoadSegment).where(RoadSegment.zone_id == zone.id)
        ).scalars().all()
        threatened_roads = [r.name for r in roads]

        results.append({
            "zone_id": zone.id,
            "zone_code": zone.code,
            "zone_name": zone.name,
            "district_code": zone.district_code,
            "hazard_index": assessment.hazard_index,
            "hazard_level": assessment.hazard_level,
            "runout": runout_data,
            "threatened_settlements": threatened_settlements,
            "threatened_roads": threatened_roads,
        })

    return {
        "count": len(results),
        "runout_profiles": results,
        "methodology": "Scheidegger-Corominas energy-angle empirical debris model",
        "validation_status": "ESTIMATED_SCENARIOS — REQUIRES EXPERT GEOTECHNICAL VALIDATION",
    }


@router.post("/simulate")
def simulate_zone_runout(
    req: RunoutSimulationRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("runout:read")),
) -> dict[str, Any]:
    """Runs a customized runout scenario with varying estimated landslide detachment volumes."""
    zone = db.get(SpatialUnit, req.zone_id)
    if not zone:
        raise HTTPException(404, "Spatial unit not found")

    elevation = float(zone.elevation_m or 450.0)
    slope = float(zone.slope_deg or 34.0)
    aspect = float(zone.aspect_deg or 195.0)

    runout_data = estimate_debris_runout(
        start_lat=zone.centroid_lat,
        start_lon=zone.centroid_lon,
        elevation_m=elevation,
        slope_deg=slope,
        aspect_deg=aspect,
        estimated_volume_m3=req.estimated_volume_m3,
    )

    return {
        "zone_id": zone.id,
        "zone_name": zone.name,
        "simulated_volume_m3": req.estimated_volume_m3,
        "runout_results": runout_data,
        "mode": "SIMULATION — NOT CONFIRMED PREDICTION",
    }
