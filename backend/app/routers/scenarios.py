"""Scenario / what-if lab. Outputs are stored separately and can never touch
operational risk, alerts, road status or notifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import request_context, require, user_scopes
from ..models import RiskAssessment, ScenarioRun, SpatialUnit
from ..services import audit, risk as risk_service
from ..services.serializers import zone_summary
from ..services.util import iso
from ..models import District

router = APIRouter(prefix="/api/v1", tags=["scenarios"])


class ScenarioInput(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    district_codes: list[str] | None = None
    rainfall_24h: float = Field(ge=0, le=600, description="Hypothetical 24-hour rainfall total (mm)")
    soil_moisture_pct: float = Field(ge=5, le=100)
    use_field_evidence: bool = False
    notes: str = Field(default="", max_length=1000)


@router.post("/scenarios", status_code=status.HTTP_201_CREATED)
def create_scenario(payload: ScenarioInput, request: Request, db: Session = Depends(get_db),
                    user=Depends(require("scenarios:run"))):
    ctx = request_context(request)
    allowed = user_scopes(user)
    targets = payload.district_codes
    if allowed is not None:
        if targets:
            outside = [c for c in targets if c not in allowed]
            if outside:
                raise HTTPException(status.HTTP_403_FORBIDDEN, f"Outside your scope: {outside}")
        else:
            targets = allowed
    if targets:
        known = {d.code for d in db.execute(select(District).where(District.code.in_(targets))).scalars()}
        missing = [c for c in targets if c not in known]
        if missing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown districts: {missing}")

    baseline_rows = risk_service.district_risk_snapshot(db, targets)
    baseline = {
        "zones": len(baseline_rows),
        "avg_hazard": round(sum(a.hazard_index for _z, _d, a in baseline_rows) / max(1, len(baseline_rows)), 2),
        "warnings": sum(1 for _z, _d, a in baseline_rows if a.hazard_level in {"WARNING", "CRITICAL"}),
        "avg_priority": round(sum(a.priority_score for _z, _d, a in baseline_rows) / max(1, len(baseline_rows)), 2),
    }

    run = ScenarioRun(
        name=payload.name, district_code=(targets[0] if targets and len(targets) == 1 else None),
        created_by=user["id"],
        inputs={
            "rainfall_24h": payload.rainfall_24h,
            "soil_moisture_pct": payload.soil_moisture_pct,
            "use_field_evidence": payload.use_field_evidence,
            "district_codes": targets,
            "notes": payload.notes,
            "assumptions": [
                "24-hour rainfall is distributed uniformly across sub-daily windows.",
                "Antecedent 72-hour rainfall is assumed to be twice the scenario 24-hour total.",
                "No forecast trajectory is generated for a hypothetical scenario.",
            ],
        },
        outputs={}, baseline_summary=baseline, note="SIMULATION — NOT LIVE",
    )
    db.add(run)
    db.flush()

    summary = risk_service.recalculate(
        db,
        district_codes=targets,
        actor=user,
        request_id=ctx["request_id"],
        reason=f"Scenario run: {payload.name}",
        scenario={
            "rainfall_24h": payload.rainfall_24h,
            "soil_moisture_pct": payload.soil_moisture_pct,
            "use_field_evidence": payload.use_field_evidence,
        },
        scenario_run_id=run.id,
    )

    scenario_assessments = list(db.execute(
        select(SpatialUnit, RiskAssessment).join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
        .where(RiskAssessment.scenario_run_id == run.id)
    ).all())
    baseline_by_zone = {z.id: a for z, _d, a in baseline_rows}
    deltas = []
    for zone, assessment in scenario_assessments:
        base = baseline_by_zone.get(zone.id)
        deltas.append({
            "zone_id": zone.id, "zone_code": zone.code, "zone_name": zone.name,
            "district_code": zone.district_code,
            "baseline_hazard": base.hazard_index if base else None,
            "scenario_hazard": assessment.hazard_index,
            "hazard_delta": round(assessment.hazard_index - (base.hazard_index if base else 0), 2),
            "baseline_priority": base.priority_level if base else None,
            "scenario_priority": assessment.priority_level,
            "scenario_exposure": assessment.exposure_score,
            "scenario_coverage": assessment.coverage_level,
            "recommended_action": (assessment.inputs or {}).get("recommended_action"),
        })
    deltas.sort(key=lambda d: d["hazard_delta"], reverse=True)
    scenario_avg = round(sum(d["scenario_hazard"] for d in deltas) / max(1, len(deltas)), 2)
    outputs = {
        "mode": "SIMULATION — NOT LIVE",
        "run_id": summary.get("run_id"),
        "zones": len(deltas),
        "avg_hazard": scenario_avg,
        "avg_hazard_delta": round(scenario_avg - baseline["avg_hazard"], 2),
        "warnings": sum(1 for d in deltas if d["scenario_hazard"] >= 60),
        "new_warnings": sum(1 for d in deltas if d["scenario_hazard"] >= 60 and (d["baseline_hazard"] or 0) < 60),
        "top_changes": deltas[:15],
        "hazard_distribution": summary.get("hazard_distribution"),
        "priority_distribution": summary.get("priority_distribution"),
        "safety_note": (
            "Scenario output is isolated. It did not create alerts, change road status or send any notification."
        ),
    }
    run.outputs = outputs
    audit.record(db, actor=user, action="scenario.run", entity="scenario", entity_id=run.id,
                 reason=payload.name,
                 payload={"inputs": run.inputs, "avg_hazard_delta": outputs["avg_hazard_delta"]},
                 request_id=ctx["request_id"], ip=ctx["ip"])
    db.commit()
    return {
        "id": run.id, "name": run.name, "created_at": iso(run.created_at),
        "badge": "SIMULATION — NOT LIVE", "inputs": run.inputs,
        "baseline": baseline, "scenario": outputs,
    }


@router.get("/scenarios")
def list_scenarios(db: Session = Depends(get_db), user=Depends(require("scenarios:run"))):
    rows = list(db.execute(select(ScenarioRun).order_by(ScenarioRun.created_at.desc()).limit(50)).scalars())
    return {
        "scenarios": [
            {
                "id": r.id, "name": r.name, "created_at": iso(r.created_at),
                "baseline": r.baseline_summary,
                "summary": {
                    "avg_hazard": (r.outputs or {}).get("avg_hazard"),
                    "avg_hazard_delta": (r.outputs or {}).get("avg_hazard_delta"),
                    "new_warnings": (r.outputs or {}).get("new_warnings"),
                },
                "badge": "SIMULATION — NOT LIVE",
            }
            for r in rows
        ]
    }


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db),
                 user=Depends(require("scenarios:run"))):
    run = db.get(ScenarioRun, scenario_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    return {
        "id": run.id, "name": run.name, "created_at": iso(run.created_at),
        "inputs": run.inputs, "baseline": run.baseline_summary, "scenario": run.outputs,
        "badge": "SIMULATION — NOT LIVE",
    }
