"""Unit tests for the BHUSHAKTI AI enhanced intelligence modules:
- Impact Analysis & Graph Connectivity Engine
- Advanced Rainfall Intelligence & Local Calibrations
- Landslide Runout & Travel-Angle Physics
- Smart Response Field Team Optimizer
- Automated Data Quality & Health Engine
- Early Warning Timeline Performance Metrics
"""

from __future__ import annotations

import pytest

from app.engine.impact import compute_settlement_isolation, find_alternative_route, haversine_distance_km
from app.engine.optimizer import rank_field_teams_for_incident
from app.engine.quality import audit_gps_coordinates, audit_report_duplicates, audit_weather_observation
from app.engine.rainfall import LOCAL_DISTRICT_CALIBRATION, evaluate_rainfall_trigger
from app.engine.runout import estimate_debris_runout
from app.engine.timeline import calculate_timeline_metrics


def test_haversine_distance():
    # Distance between Guwahati (26.18, 91.75) and Shillong (25.57, 91.89) is ~70-75 km
    dist = haversine_distance_km(26.18, 91.75, 25.57, 91.89)
    assert 65.0 < dist < 80.0


def test_impact_road_blockage_isolation():
    settlements = [
        {"id": 1, "name": "Sonapur Foothills", "lat": 26.11, "lon": 91.78, "population_estimate": 1200},
        {"id": 2, "name": "Dispur Core", "lat": 26.14, "lon": 91.79, "population_estimate": 15000},
    ]
    roads = [
        {
            "id": 10,
            "name": "GS Road Highway",
            "segments": [
                {"id": 101, "name": "Sonapur Pass Cut", "length_km": 3.5, "status": "OPEN"},
                {"id": 102, "name": "Dispur Flyover", "length_km": 2.0, "status": "OPEN"},
            ],
        }
    ]
    # Block segment 101
    result = compute_settlement_isolation(
        settlements=settlements,
        roads=roads,
        blocked_segment_ids={101},
        district_hq_coord=(26.14, 91.77),
    )
    assert result["total_isolated_count"] >= 1
    assert any(s["name"] == "Sonapur Foothills" for s in result["isolated_settlements"])


def test_alternative_route_computation():
    route = find_alternative_route((26.14, 91.77), (26.11, 91.78), ["Sonapur Pass Cut"])
    assert route["alternative_available"] is True
    assert route["detour_distance_km"] > route["original_direct_distance_km"]
    assert "Sonapur Pass Cut" in route["avoided_blockages"]


def test_district_rainfall_local_calibration():
    # East Khasi Hills (Cherrapunji regime) must have higher threshold than Kamrup (weathered red soil)
    kmr = LOCAL_DISTRICT_CALIBRATION["AS-KMR"]
    ekh = LOCAL_DISTRICT_CALIBRATION["ML-EKH"]
    assert ekh["threshold_24h_warning_mm"] > kmr["threshold_24h_warning_mm"]
    assert ekh["threshold_24h_critical_mm"] > kmr["threshold_24h_critical_mm"]

    # 100mm in Kamrup should exceed warning threshold
    kmr_res = evaluate_rainfall_trigger("AS-KMR", 10.0, 45.0, 105.0, 180.0, 52.0)
    assert kmr_res["threshold_status"] in {"WARNING_EXCEEDED", "CRITICAL_EXCEEDED"}

    # 100mm in East Khasi Hills is within normal operational monsoon range (< 145mm warning)
    ekh_res = evaluate_rainfall_trigger("ML-EKH", 10.0, 45.0, 100.0, 180.0, 52.0)
    assert ekh_res["threshold_status"] == "WATCH_EXCEEDED"  # watch is 85mm, warn is 145mm


def test_landslide_runout_estimation():
    runout = estimate_debris_runout(
        start_lat=26.15,
        start_lon=91.78,
        elevation_m=350.0,
        slope_deg=35.0,
        aspect_deg=180.0,
        estimated_volume_m3=12000.0,
    )
    assert runout["max_runout_length_m"] > 100.0
    assert runout["fahrboschung_angle_deg"] > 10.0
    assert runout["runout_hazard_class"] in {"HIGH", "EXTREME"}
    assert len(runout["downslope_flowline_geojson"]["geometry"]["coordinates"]) == 9


def test_smart_response_optimizer_ranking():
    incident = {"lat": 26.15, "lon": 91.78, "hazard_type": "SLOPE_MOVEMENT", "priority": "P1"}
    teams = [
        {"id": 1, "name": "Team Close Available", "base_lat": 26.16, "base_lon": 91.78, "status": "AVAILABLE", "specialization": "GEOTECHNICAL_ASSESSMENT", "current_active_assignments": 0},
        {"id": 2, "name": "Team Far Busy", "base_lat": 26.35, "base_lon": 91.95, "status": "AVAILABLE", "specialization": "SEARCH_AND_RESCUE", "current_active_assignments": 3},
    ]
    ranked = rank_field_teams_for_incident(incident, teams, set())
    assert ranked[0]["team_id"] == 1
    assert ranked[0]["rank"] == 1
    assert ranked[0]["composite_score"] > ranked[1]["composite_score"]


def test_data_quality_audits():
    # Valid GPS inside district
    valid_gps = audit_gps_coordinates(26.15, 91.77, {"min_lat": 25.8, "min_lon": 91.5, "max_lat": 26.5, "max_lon": 92.2})
    assert valid_gps["status"] == "VERIFIED"

    # Outlier GPS outside district
    outlier_gps = audit_gps_coordinates(28.5, 77.2, {"min_lat": 25.8, "min_lon": 91.5, "max_lat": 26.5, "max_lon": 92.2})
    assert outlier_gps["status"] == "WARNING"

    # Negative rainfall
    neg_rain_issues = audit_weather_observation(-5.0, -10.0, 45.0, None)
    assert any(i["status"] == "INVALID" for i in neg_rain_issues)

    # Duplicate reports
    r1 = {"id": 1, "lat": 26.1501, "lon": 91.7701}
    r2 = {"id": 2, "lat": 26.1502, "lon": 91.7702}
    dup_res = audit_report_duplicates(r2, [r1], distance_threshold_m=100.0)
    assert dup_res["is_duplicate"] is True
    assert dup_res["status"] == "WARNING"


def test_timeline_performance_metrics():
    events = [
        {"milestone": "FIRST_DETECTED", "occurred_at": "2026-07-01T08:00:00+00:00"},
        {"milestone": "ALERT_GENERATED", "occurred_at": "2026-07-01T10:00:00+00:00"},
        {"milestone": "ALERT_APPROVED", "occurred_at": "2026-07-01T10:18:00+00:00"},
        {"milestone": "NOTIFICATION_DELIVERED", "occurred_at": "2026-07-01T10:22:00+00:00"},
        {"milestone": "TEAM_ASSIGNED", "occurred_at": "2026-07-01T10:45:00+00:00"},
        {"milestone": "INCIDENT_OCCURRED", "occurred_at": "2026-07-01T15:30:00+00:00"},
    ]
    metrics = calculate_timeline_metrics(events)
    assert metrics["decision_latency_minutes"] == 18
    assert metrics["dispatch_latency_minutes"] == 27
    assert metrics["warning_lead_time_hours"] == 5.1
    assert metrics["overall_effectiveness_score"] >= 80.0
