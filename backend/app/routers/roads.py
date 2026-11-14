"""Road network intelligence with an explicit separation of model estimate,
officer verification and official closure."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..domain import RoadStatus, RoadStatusSource
from ..models import District, Road, RoadSegment, SpatialUnit
from ..services import audit
from ..services.events import bus
from ..services.serializers import segment_dict
from ..services.util import iso

router = APIRouter(prefix="/api/v1", tags=["roads"])


class RoadStatusUpdate(BaseModel):
    status: RoadStatus
    status_source: RoadStatusSource = RoadStatusSource.OFFICER_VERIFIED
    evidence: str = Field(min_length=4, max_length=2000)
    reason: str = Field(default="", max_length=400)


@router.get("/roads")
def roads(
    db: Session = Depends(get_db),
    user=Depends(require("roads:read")),
    district_code: str | None = None,
    status_filter: str | None = None,
):
    allowed = user_scopes(user)
    stmt = select(Road)
    roads_rows = list(db.execute(stmt).scalars())
    segments = list(db.execute(select(RoadSegment)).scalars())
    zones = {z.id: z for z in db.execute(select(SpatialUnit)).scalars()}
    districts = {d.code: d for d in db.execute(select(District)).scalars()}

    out = []
    for road in roads_rows:
        codes = road.district_codes or []
        if district_code and district_code not in codes:
            continue
        if allowed is not None and not set(codes).intersection(allowed):
            continue
        road_segments = []
        for segment in segments:
            zone = zones.get(segment.zone_id)
            if zone is None:
                continue
            if district_code and zone.district_code != district_code:
                continue
            if allowed is not None and zone.district_code not in allowed:
                continue
            if status_filter and segment.status != status_filter.upper():
                continue
            road_segments.append({
                **segment_dict(segment),
                "zone_name": zone.name,
                "district_code": zone.district_code,
                "district_name": districts[zone.district_code].name if zone.district_code in districts else None,
                "centroid": {"lat": zone.centroid_lat, "lon": zone.centroid_lon},
            })
        if not road_segments and (status_filter or district_code):
            continue
        out.append({
            "id": road.id,
            "ref": road.ref,
            "name": road.name,
            "road_class": road.road_class,
            "district_codes": codes,
            "geometry": road.geometry,
            "source": road.source,
            "geometry_note": road.geometry_note,
            "segments": road_segments,
        })
    return {
        "roads": out,
        "status_definitions": {
            "MODEL_ESTIMATED": "Model-estimated risk derived from the hazard assessment. Not an observation.",
            "OFFICER_VERIFIED": "Status confirmed by an authorised officer, with evidence.",
            "OFFICIAL_CLOSURE": "Closure declared through official channels.",
        },
        "note": "Model-estimated risk, officer-verified status and official closure are not interchangeable.",
    }


@router.patch("/roads/segments/{segment_id}/status")
def update_segment_status(segment_id: int, payload: RoadStatusUpdate, request: Request,
                          db: Session = Depends(get_db), user=Depends(require("roads:write"))):
    ctx = request_context(request)
    segment = db.get(RoadSegment, segment_id)
    if segment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Road segment not found")
    zone = db.get(SpatialUnit, segment.zone_id) if segment.zone_id else None
    allowed = user_scopes(user)
    if zone is not None and allowed is not None and zone.district_code not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outside your authorised district scope")
    if payload.status_source == RoadStatusSource.MODEL_ESTIMATED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Officers cannot write a MODEL_ESTIMATED status; it is produced by the risk engine")
    previous = {"status": segment.status, "source": segment.status_source, "evidence": segment.evidence}
    segment.status = payload.status.value
    segment.status_source = payload.status_source.value
    segment.status_updated_at = datetime.now(timezone.utc)
    segment.status_updated_by = user["id"]
    segment.evidence = payload.evidence
    audit.record(
        db, actor=user, action="road.status_updated", entity="road_segment", entity_id=segment.id,
        reason=payload.reason or f"Status set to {payload.status.value}",
        payload={"before": previous, "after": {"status": segment.status, "source": segment.status_source,
                                               "evidence": payload.evidence}},
        request_id=ctx["request_id"], ip=ctx["ip"],
    )
    db.commit()
    bus.publish("road.updated", {"id": segment.id, "status": segment.status})
    return {**segment_dict(segment), "previous": previous, "updated_at": iso(segment.status_updated_at)}
