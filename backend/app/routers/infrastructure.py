"""Exposure assets and historical inventory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require, user_scopes
from ..models import District, InfrastructureAsset, LandslideIncident, SpatialUnit
from ..services.util import iso

router = APIRouter(prefix="/api/v1", tags=["exposure"])


@router.get("/infrastructure")
def infrastructure(
    db: Session = Depends(get_db),
    user=Depends(require("infra:read")),
    district_code: str | None = None,
    kind: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
):
    allowed = user_scopes(user)
    stmt = select(InfrastructureAsset)
    if district_code:
        stmt = stmt.where(InfrastructureAsset.district_code == district_code)
    elif allowed is not None:
        stmt = stmt.where(InfrastructureAsset.district_code.in_(allowed))
    if kind:
        stmt = stmt.where(InfrastructureAsset.kind == kind)
    rows = list(db.execute(stmt.limit(limit)).scalars())
    return {
        "assets": [
            {
                "id": a.id, "kind": a.kind, "name": a.name, "lat": a.lat, "lon": a.lon,
                "district_code": a.district_code, "capacity": a.capacity,
                "population_estimate": a.population_estimate,
                "source": a.source, "source_state": a.source_state,
            }
            for a in rows
        ],
        "counts": {
            kind_name: sum(1 for a in rows if a.kind == kind_name)
            for kind_name in {a.kind for a in rows}
        },
        "note": "Population and facility values are demonstration estimates, not authoritative counts.",
    }


@router.get("/incidents")
def incidents(
    db: Session = Depends(get_db),
    user=Depends(require("incidents:read")),
    district_code: str | None = None,
    verified_only: bool = False,
    limit: int = Query(default=300, ge=1, le=1000),
):
    allowed = user_scopes(user)
    stmt = select(LandslideIncident)
    if district_code:
        stmt = stmt.where(LandslideIncident.district_code == district_code)
    elif allowed is not None:
        stmt = stmt.where(LandslideIncident.district_code.in_(allowed))
    if verified_only:
        stmt = stmt.where(LandslideIncident.verified.is_(True))
    rows = list(db.execute(stmt.order_by(LandslideIncident.occurred_on.desc()).limit(limit)).scalars())
    zones = {z.id: z for z in db.execute(select(SpatialUnit)).scalars()}
    districts = {d.code: d for d in db.execute(select(District)).scalars()}
    return {
        "incidents": [
            {
                "id": i.id, "district_code": i.district_code,
                "district_name": districts[i.district_code].name if i.district_code in districts else i.district_code,
                "zone_id": i.zone_id, "zone_name": zones[i.zone_id].name if i.zone_id in zones else None,
                "occurred_on": i.occurred_on.isoformat(),
                "date_uncertainty_days": i.date_uncertainty_days,
                "lat": i.lat, "lon": i.lon, "location_accuracy_m": i.location_accuracy_m,
                "verified": i.verified, "source": i.source, "description": i.description,
            }
            for i in rows
        ],
        "verified_count": sum(1 for i in rows if i.verified),
        "synthetic_warning": (
            "Rows marked SIMULATED are demonstration records and must not be used as training or "
            "validation evidence."
        ),
        "generated_at": iso(__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    }
