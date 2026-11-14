"""Impact Analysis and Road Network Graph Connectivity Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require
from ..engine.impact import compute_settlement_isolation, find_alternative_route, haversine_distance_km
from ..models import District, EmergencyFacility, InfrastructureAsset, RiskAssessment, Road, RoadSegment, SpatialUnit

router = APIRouter(prefix="/api/v1/impact", tags=["impact"])


class SimulateBlockageRequest(BaseModel):
    district_code: str = Field(default="AS-KMR")
    blocked_segment_ids: list[int] = Field(default_factory=list)


@router.get("/summary")
def get_impact_summary(
    district_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("risk:read")),
) -> dict[str, Any]:
    """Provides geospatial impact exposure metrics across roads, settlements, and facilities."""
    district_filter = [district_code] if district_code else None

    # Load spatial units with high hazard
    stmt = (
        select(SpatialUnit, RiskAssessment)
        .join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
        .where(RiskAssessment.hazard_level.in_(["WARNING", "CRITICAL"]))
    )
    if district_filter:
        stmt = stmt.where(SpatialUnit.district_code.in_(district_filter))
    
    high_risk_zones = db.execute(stmt).all()
    high_risk_zone_ids = {z.id for z, _ in high_risk_zones}

    # Blocked or at-risk road segments
    road_stmt = select(RoadSegment).where(RoadSegment.zone_id.in_(high_risk_zone_ids))
    impacted_segments = db.execute(road_stmt).scalars().all()

    # Settlements in district
    asset_stmt = select(InfrastructureAsset).where(InfrastructureAsset.kind == "settlements")
    if district_filter:
        asset_stmt = asset_stmt.where(InfrastructureAsset.district_code.in_(district_filter))
    settlements = db.execute(asset_stmt).scalars().all()

    # Hospitals / Facilities
    fac_stmt = select(EmergencyFacility)
    if district_filter:
        fac_stmt = fac_stmt.where(EmergencyFacility.district_code.in_(district_filter))
    facilities = db.execute(fac_stmt).scalars().all()

    total_exposed_pop = sum(int(s.population_estimate or 450) for s in settlements if s.district_code in (district_filter or [s.district_code]))
    
    return {
        "district_code": district_code or "ALL",
        "high_risk_zones_count": len(high_risk_zones),
        "impacted_road_segments_count": len(impacted_segments),
        "total_exposed_population": total_exposed_pop,
        "emergency_facilities_active": len([f for f in facilities if f.status == "OPERATIONAL"]),
        "hospitals_ready": len([f for f in facilities if f.kind == "HOSPITAL" and f.status == "OPERATIONAL"]),
        "shelters_ready": len([f for f in facilities if f.kind in {"SHELTER", "SCHOOL_SHELTER"} and f.status == "OPERATIONAL"]),
        "status_notice": "AI-generated estimate — requires verification against on-ground emergency reports",
    }


@router.post("/simulate-blockage")
def simulate_road_blockage(
    req: SimulateBlockageRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("risk:read")),
) -> dict[str, Any]:
    """Graph connectivity analysis: recalculates isolated settlements and alternative routes when road segments are blocked."""
    district = db.get(District, req.district_code)
    if not district:
        raise HTTPException(404, "District not found")

    # Load all roads in district
    roads = db.execute(select(Road)).scalars().all()
    road_dicts = []
    for r in roads:
        if req.district_code in r.district_codes:
            segments = db.execute(select(RoadSegment).where(RoadSegment.road_id == r.id)).scalars().all()
            road_dicts.append({
                "id": r.id,
                "name": r.name,
                "ref": r.ref,
                "segments": [{"id": s.id, "name": s.name, "length_km": s.length_km, "status": s.status} for s in segments],
            })

    # Load settlements
    assets = db.execute(
        select(InfrastructureAsset).where(
            InfrastructureAsset.district_code == req.district_code,
            InfrastructureAsset.kind == "settlements",
        )
    ).scalars().all()
    settlement_dicts = [{"id": a.id, "name": a.name, "lat": a.lat, "lon": a.lon, "population_estimate": a.population_estimate} for a in assets]

    # Calculate isolation
    blocked_set = set(req.blocked_segment_ids)
    isolation_result = compute_settlement_isolation(
        settlement_dicts,
        road_dicts,
        blocked_set,
        (district.lat, district.lon),
    )

    # Compute alternative bypass route
    alt_route = find_alternative_route(
        (district.lat, district.lon),
        (district.lat + 0.08, district.lon + 0.08),
        [f"Segment #{s_id}" for s_id in req.blocked_segment_ids],
    )

    return {
        "district_code": req.district_code,
        "blocked_segments_evaluated": list(blocked_set),
        "total_isolated_settlements": isolation_result["total_isolated_count"],
        "total_exposed_population": isolation_result["total_exposed_population"],
        "isolated_settlements": isolation_result["isolated_settlements"],
        "connected_settlements_sample": isolation_result["connected_settlements"][:5],
        "alternative_emergency_route": alt_route,
        "classification": "HYPOTHETICAL_SIMULATION",
        "data_disclaimer": "AI-generated estimate — requires verification before deploying emergency convoys",
    }
