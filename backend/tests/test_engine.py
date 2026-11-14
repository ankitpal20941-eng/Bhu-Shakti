"""Unit tests for the risk engine. These encode the scientific and safety rules."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.engine import params as P
from app.engine.exposure import compute_exposure, compute_priority, compute_vulnerability
from app.engine.hazard import (
    combine_hazard,
    coverage_and_uncertainty,
    dynamic_trigger,
    field_evidence_adjustment,
    id_threshold_mm_per_h,
    static_susceptibility,
)
from app.engine.trajectory import build_trajectory


def zone(**overrides):
    base = dict(
        slope_deg=22.0, terrain_ruggedness=120.0, curvature=0.2, elevation_m=1200.0,
        twi=8.4, aspect_deg=200.0, landcover="shrub", geology="schist_phyllite",
        road_cut_proximity_m=250.0, centroid_lat=25.5, centroid_lon=91.9,
        bbox_json={"min_lat": 25.47, "max_lat": 25.52, "min_lon": 91.87, "max_lon": 91.92},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_static_decomposition_is_exact_and_bounded():
    result = static_susceptibility(zone())
    assert 0 <= result.index <= 100
    assert math.isclose(P.INTERCEPT + sum(t["log_odds"] for t in result.terms), result.logit, abs_tol=1e-3)
    assert result.probability_uncalibrated == pytest.approx(1 / (1 + math.exp(-result.logit)), abs=1e-5)


def test_static_missing_features_are_reported():
    result = static_susceptibility(zone(slope_deg=None, twi=None))
    assert "slope_deg" in result.missing and "twi" in result.missing
    assert result.out_of_domain is True


def test_id_threshold_decreases_with_duration():
    assert id_threshold_mm_per_h(1) > id_threshold_mm_per_h(24) > id_threshold_mm_per_h(72)
    assert id_threshold_mm_per_h(24) == pytest.approx(P.ID_A * 24 ** P.ID_B * P.ID_REGIONAL_FACTOR, rel=1e-6)


def test_dry_weather_cannot_produce_high_hazard():
    """A steep slope with no rain is primed, not critical."""
    hazard, breakdown = combine_hazard(95.0, 0.0, trigger_available=True)
    assert hazard == pytest.approx(95.0 * P.TRIGGER_FLOOR, abs=0.01)
    assert hazard < 30
    assert breakdown["trigger_multiplier"] == pytest.approx(P.TRIGGER_FLOOR)


def test_trigger_scales_hazard_up_to_susceptibility():
    hazard, _ = combine_hazard(80.0, 100.0, trigger_available=True)
    assert hazard == pytest.approx(80.0, abs=0.5)
    hazard_mid, _ = combine_hazard(80.0, 50.0, trigger_available=True)
    assert P.TRIGGER_FLOOR * 80 < hazard_mid < 80


def test_missing_trigger_uses_midrange_and_lowers_confidence():
    hazard, breakdown = combine_hazard(80.0, 0.0, trigger_available=False)
    assert hazard == pytest.approx(80.0 * P.TRIGGER_UNAVAILABLE_MULTIPLIER, abs=0.01)
    coverage = coverage_and_uncertainty(
        weather_state="UNAVAILABLE", weather_age_minutes=None, soil_moisture_present=False,
        terrain_source="DEM-derived (live)", verified_inventory_count=0,
        landcover_source="Demo assignment (SIMULATED)",
    )
    assert coverage["level"] == "LOW"
    assert any("Rainfall: unavailable" in r for r in coverage["reasons"])


def test_heavy_rain_produces_high_trigger_ratio():
    trigger = dynamic_trigger(
        rainfall_1h=25, rainfall_6h=90, rainfall_24h=240, rainfall_72h=380,
        forecast_24h=120, soil_moisture_pct=50, month=7,
    )
    assert trigger.available is True
    assert trigger.index > 50
    assert trigger.components["ratios"]["r_24h"] > 1


def test_field_evidence_ignores_unverified_and_caps_total():
    now = datetime.now(timezone.utc)
    unverified = [{"id": 1, "status": "PENDING_VERIFICATION", "hazard_type": "SLOPE_MOVEMENT",
                   "observed_at": now}]
    assert field_evidence_adjustment(unverified, now=now)["applied_points"] == 0

    many_verified = [
        {"id": i, "status": "VERIFIED", "hazard_type": "SLOPE_MOVEMENT", "observed_at": now}
        for i in range(10)
    ]
    result = field_evidence_adjustment(many_verified, now=now)
    assert result["applied_points"] == P.FIELD_EVIDENCE_MAX_POINTS


def test_field_evidence_decays_and_expires():
    now = datetime.now(timezone.utc)
    fresh = [{"id": 1, "status": "VERIFIED", "hazard_type": "GROUND_CRACK", "observed_at": now}]
    old = [{"id": 2, "status": "VERIFIED", "hazard_type": "GROUND_CRACK",
            "observed_at": now - timedelta(days=10)}]
    expired = [{"id": 3, "status": "VERIFIED", "hazard_type": "GROUND_CRACK",
                "observed_at": now - timedelta(days=20)}]
    assert field_evidence_adjustment(fresh, now=now)["applied_points"] > \
        field_evidence_adjustment(old, now=now)["applied_points"]
    assert field_evidence_adjustment(expired, now=now)["applied_points"] == 0


def test_trajectory_only_reports_available_horizons():
    trajectory = build_trajectory(
        static_index=70.0, rainfall_1h=10, rainfall_6h=40, rainfall_24h=120, rainfall_72h=200,
        soil_moisture_pct=45, month=7, forecasts={6: 30, 24: 90}, forecast_issued_at="2026-07-01T00:00:00Z",
    )
    assert trajectory["supported_horizons"] == [6, 24]
    assert 12 in trajectory["unavailable_horizons"]
    assert 48 in trajectory["unavailable_horizons"]
    assert all(p["probability_status"] == "NOT_CALIBRATED" for p in trajectory["points"])
    assert all("reason" in m for m in trajectory["missing"])


def test_no_forecast_means_no_trajectory_points():
    trajectory = build_trajectory(
        static_index=70.0, rainfall_1h=10, rainfall_6h=40, rainfall_24h=120, rainfall_72h=200,
        soil_moisture_pct=45, month=7, forecasts={}, forecast_issued_at=None,
    )
    assert trajectory["points"] == []
    assert set(trajectory["unavailable_horizons"]) == set(P.FORECAST_HORIZONS)


def test_exposure_counts_assets_inside_unit():
    assets = [
        {"kind": "settlements", "name": "Inside", "lat": 25.49, "lon": 91.89,
         "population_estimate": 5000, "source": "demo", "source_state": "SIMULATED"},
        {"kind": "hospital", "name": "Far away", "lat": 30.0, "lon": 80.0,
         "population_estimate": None, "source": "demo", "source_state": "SIMULATED"},
    ]
    result = compute_exposure(zone(), assets=assets, road_segments=[])
    assert result.counts["settlements"] == 1
    assert result.counts["hospitals"] == 0
    assert result.population_exposed == 5000
    assert 0 < result.score < 100


def test_priority_is_separate_from_hazard():
    high_hazard_no_exposure = compute_priority(90.0, 0.0, 0.0)
    moderate_hazard_high_exposure = compute_priority(60.0, 100.0, 80.0)
    # A severe hazard with nothing exposed is not automatically the top priority.
    assert high_hazard_no_exposure["level"] == "P3"
    assert moderate_hazard_high_exposure["score"] > high_hazard_no_exposure["score"]
    assert moderate_hazard_high_exposure["level"] in {"P2", "P1"}
    assert set(high_hazard_no_exposure["contributions"]) == {"hazard", "exposure", "vulnerability"}


def test_vulnerability_inputs_are_reported():
    exposure = compute_exposure(zone(), assets=[], road_segments=[{"length_km": 3.0}])
    vulnerability = compute_vulnerability(
        exposure=exposure, district_asset_max={"settlements": 10},
        nearest_hospital_km=18.0, landcover="shrub",
    )
    assert 0 <= vulnerability["score"] <= 100
    assert vulnerability["nearest_hospital_km"] == 18.0
    assert "weights" in vulnerability
