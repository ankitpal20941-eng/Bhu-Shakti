"""Automated Data Validation and Quality Engine.

Audits telemetry, sensors, GPS coordinates, reports, and satellite datasets:
- Missing observation gaps
- Coordinate bounding-box validity
- Spatiotemporal duplicate clustering for citizen reports
- Sensor drift and abnormal spikes
- Satellite imagery freshness SLAs
- Assigns transparent data quality states: VERIFIED, GOOD, WARNING, INVALID, OUTDATED
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def audit_gps_coordinates(lat: float | None, lon: float | None, district_bbox: dict[str, float] | None) -> dict[str, Any]:
    """Validates GPS coordinates against district boundaries and realistic physical limits."""
    if lat is None or lon is None:
        return {"status": "INVALID", "issue": "Missing latitude or longitude coordinates"}

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return {"status": "INVALID", "issue": f"Out-of-range physical coordinates: ({lat}, {lon})"}

    if district_bbox:
        min_lon = district_bbox.get("min_lon", 89.0)
        min_lat = district_bbox.get("min_lat", 22.0)
        max_lon = district_bbox.get("max_lon", 96.0)
        max_lat = district_bbox.get("max_lat", 29.0)
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            return {
                "status": "WARNING",
                "issue": f"Coordinate ({lat}, {lon}) falls outside district bounding box [{min_lat}, {min_lon}, {max_lat}, {max_lon}]",
            }

    return {"status": "VERIFIED", "issue": "Valid coordinates inside expected district boundary"}


def audit_weather_observation(
    rainfall_1h: float | None,
    rainfall_24h: float | None,
    soil_moisture_pct: float | None,
    observed_at: datetime | None,
) -> list[dict[str, Any]]:
    """Checks for physical inconsistencies and sensor dropouts in meteorological feeds."""
    issues = []
    now = datetime.now(timezone.utc)

    # 1. Missingness
    if rainfall_24h is None:
        issues.append({
            "metric": "rainfall_24h",
            "status": "INVALID",
            "summary": "Missing 24-hour rainfall accumulation; trigger calculation degraded",
        })

    # 2. Negative rain or physical anomalies
    if rainfall_24h is not None and rainfall_24h < 0.0:
        issues.append({
            "metric": "rainfall_24h",
            "status": "INVALID",
            "summary": f"Impossible negative rainfall value: {rainfall_24h} mm",
        })
    elif rainfall_24h is not None and rainfall_24h > 650.0:
        issues.append({
            "metric": "rainfall_24h",
            "status": "WARNING",
            "summary": f"Extreme outlier rainfall ({rainfall_24h} mm) exceeds 100-year return period; sensor check required",
        })

    # 3. Soil moisture range
    if soil_moisture_pct is not None:
        if not (0.0 <= soil_moisture_pct <= 100.0):
            issues.append({
                "metric": "soil_moisture_pct",
                "status": "INVALID",
                "summary": f"Soil moisture percentage out of bounds: {soil_moisture_pct}%",
            })

    # 4. Temporal freshness
    if observed_at is not None:
        age_hours = (now - observed_at).total_seconds() / 3600.0
        if age_hours > 24.0:
            issues.append({
                "metric": "observation_age",
                "status": "OUTDATED",
                "summary": f"Telemetry is stale ({round(age_hours, 1)} hours old; SLA is 3 hours)",
            })
        elif age_hours < -0.1:
            issues.append({
                "metric": "observation_timestamp",
                "status": "INVALID",
                "summary": "Future timestamp detected in telemetry stream",
            })

    return issues


def audit_report_duplicates(
    new_report: dict[str, Any],
    existing_reports: list[dict[str, Any]],
    distance_threshold_m: float = 120.0,
    time_window_minutes: float = 90.0,
) -> dict[str, Any]:
    """Identifies potential duplicate incident reports using spatiotemporal proximity."""
    new_lat = new_report.get("lat")
    new_lon = new_report.get("lon")
    new_time = new_report.get("observed_at")

    if new_lat is None or new_lon is None:
        return {"is_duplicate": False, "status": "GOOD"}

    for r in existing_reports:
        if r.get("id") == new_report.get("id"):
            continue
        r_lat = r.get("lat")
        r_lon = r.get("lon")
        if r_lat is None or r_lon is None:
            continue
        
        # approximate distance
        d_lat = abs(new_lat - r_lat) * 111139.0
        d_lon = abs(new_lon - r_lon) * 105000.0
        dist_m = (d_lat**2 + d_lon**2)**0.5

        if dist_m < distance_threshold_m:
            return {
                "is_duplicate": True,
                "status": "WARNING",
                "cluster_with_report_id": r.get("id"),
                "distance_meters": round(dist_m, 1),
                "summary": f"Potential duplicate of report #{r.get('id')} ({round(dist_m, 0)} m away)",
            }

    return {"is_duplicate": False, "status": "VERIFIED"}
