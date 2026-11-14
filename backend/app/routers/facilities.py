"""Emergency Facility and Evacuation Support Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require
from ..engine.impact import haversine_distance_km
from ..models import EmergencyFacility

router = APIRouter(prefix="/api/v1/facilities", tags=["facilities"])


class CreateFacilityRequest(BaseModel):
    district_code: str
    kind: str
    name: str
    lat: float
    lon: float
    capacity: int = 150
    contact_phone: str = ""
    contact_officer: str = ""
    power_backup: bool = True
    water_supply: bool = True
    medical_supplies: bool = True
    address: str = ""


class UpdateFacilityRequest(BaseModel):
    status: str | None = None
    current_occupancy: int | None = None
    power_backup: bool | None = None
    water_supply: bool | None = None
    medical_supplies: bool | None = None
    notes: str | None = None


@router.get("")
def list_facilities(
    district_code: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("facilities:read")),
) -> dict[str, Any]:
    """Retrieves verified emergency shelters, hospitals, and disaster facilities."""
    stmt = select(EmergencyFacility)
    if district_code:
        stmt = stmt.where(EmergencyFacility.district_code == district_code)
    if kind:
        stmt = stmt.where(EmergencyFacility.kind == kind)
    if status:
        stmt = stmt.where(EmergencyFacility.status == status)

    facilities = db.execute(stmt).scalars().all()

    return {
        "count": len(facilities),
        "facilities": [
            {
                "id": f.id,
                "district_code": f.district_code,
                "kind": f.kind,
                "name": f.name,
                "lat": f.lat,
                "lon": f.lon,
                "capacity": f.capacity,
                "current_occupancy": f.current_occupancy,
                "available_capacity": max(0, f.capacity - f.current_occupancy),
                "contact_phone": f.contact_phone,
                "contact_officer": f.contact_officer,
                "power_backup": f.power_backup,
                "water_supply": f.water_supply,
                "medical_supplies": f.medical_supplies,
                "status": f.status,
                "address": f.address,
                "verified_by_authority": f.verified_by_authority,
            }
            for f in facilities
        ],
        "evacuation_authority_notice": (
            "NOTICE: Emergency evacuation orders and shelter assignments are strictly issued by "
            "District Disaster Management Authorities (DDMA). BHUSHAKTI AI does not auto-order evacuations."
        ),
    }


@router.get("/nearby")
def find_nearby_facilities(
    lat: float = Query(...),
    lon: float = Query(...),
    max_distance_km: float = Query(default=25.0),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("facilities:read")),
) -> dict[str, Any]:
    """Finds closest operational shelters and hospitals to an incident or risk coordinate."""
    all_facs = db.execute(select(EmergencyFacility).where(EmergencyFacility.status == "OPERATIONAL")).scalars().all()
    with_distance = []
    for f in all_facs:
        d = haversine_distance_km(lat, lon, f.lat, f.lon)
        if d <= max_distance_km:
            with_distance.append({
                "facility": {
                    "id": f.id,
                    "name": f.name,
                    "kind": f.kind,
                    "capacity": f.capacity,
                    "available_beds": max(0, f.capacity - f.current_occupancy),
                    "phone": f.contact_phone,
                },
                "distance_km": round(d, 2),
                "estimated_transit_min": int((d / 30.0) * 60) + 5,
            })

    with_distance.sort(key=lambda x: x["distance_km"])
    return {"nearby_facilities": with_distance[:10]}


@router.post("")
def create_facility(
    req: CreateFacilityRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("facilities:write")),
) -> dict[str, Any]:
    """Authorized administrator endpoint to register a new emergency facility or shelter."""
    fac = EmergencyFacility(
        district_code=req.district_code,
        kind=req.kind,
        name=req.name,
        lat=req.lat,
        lon=req.lon,
        capacity=req.capacity,
        current_occupancy=0,
        contact_phone=req.contact_phone,
        contact_officer=req.contact_officer,
        power_backup=req.power_backup,
        water_supply=req.water_supply,
        medical_supplies=req.medical_supplies,
        address=req.address,
        status="OPERATIONAL",
        verified_by_authority=True,
    )
    db.add(fac)
    db.commit()
    db.refresh(fac)
    return {"status": "created", "facility_id": fac.id, "name": fac.name}


@router.patch("/{facility_id}")
def update_facility(
    facility_id: int,
    req: UpdateFacilityRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require("facilities:write")),
) -> dict[str, Any]:
    """Updates operational readiness and occupancy of an emergency facility."""
    fac = db.get(EmergencyFacility, facility_id)
    if not fac:
        raise HTTPException(404, "Facility not found")

    if req.status is not None:
        fac.status = req.status
    if req.current_occupancy is not None:
        fac.current_occupancy = req.current_occupancy
    if req.power_backup is not None:
        fac.power_backup = req.power_backup
    if req.water_supply is not None:
        fac.water_supply = req.water_supply
    if req.medical_supplies is not None:
        fac.medical_supplies = req.medical_supplies

    db.commit()
    return {"status": "updated", "facility_id": fac.id, "occupancy": fac.current_occupancy, "operational_status": fac.status}
