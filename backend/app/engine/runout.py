"""Landslide Runout and Downslope Debris Impact Zone Analysis Engine.

Estimates potential debris travel distance, runout path geometry, and impacted assets
using empirical energy-line (Fahrböschung / travel-angle) and slope-gradient physics.

IMPORTANT SAFETY NOTICE:
Outputs represent estimated scenario envelopes, not definitive runout predictions.
Physical slope failure trajectories require geotechnical site investigation and LiDAR DEM verification.
"""

from __future__ import annotations

import math
from typing import Any


def estimate_debris_runout(
    start_lat: float,
    start_lon: float,
    elevation_m: float,
    slope_deg: float,
    aspect_deg: float,
    estimated_volume_m3: float = 8500.0,
) -> dict[str, Any]:
    """Computes empirical runout travel distance (L) and trajectory path using the Scheidegger-Corominas relation."""
    # Travel angle (alpha) decreases with volume: tan(alpha) = 0.95 * V^(-0.09) for debris flows / slides
    vol_clamped = max(500.0, min(500000.0, estimated_volume_m3))
    tan_alpha = 0.95 * (vol_clamped ** -0.09)
    runout_angle_deg = math.degrees(math.atan(tan_alpha))

    # Fall height estimation based on slope gradient
    fall_height_m = max(25.0, min(elevation_m * 0.45, 120.0 + (slope_deg * 4.5)))
    
    # Runout length L = H / tan(alpha)
    runout_length_m = min(1800.0, max(80.0, fall_height_m / tan_alpha))

    # Compute downslope trajectory path coordinates following aspect direction
    # Aspect is the direction the slope faces (0 = North, 90 = East, 180 = South, 270 = West)
    rad_aspect = math.radians(aspect_deg)
    
    # 1 degree lat is ~111,000 meters; 1 degree lon is ~111,000 * cos(lat)
    meters_to_lat = 1.0 / 111139.0
    meters_to_lon = 1.0 / (111139.0 * math.cos(math.radians(start_lat)))

    steps = 8
    path_points = []
    for step in range(steps + 1):
        frac = step / float(steps)
        dist_m = runout_length_m * frac
        # slight meandering effect based on sin curve
        meander = math.sin(frac * math.pi) * 22.0
        d_north = (dist_m * math.cos(rad_aspect)) - (meander * math.sin(rad_aspect))
        d_east = (dist_m * math.sin(rad_aspect)) + (meander * math.cos(rad_aspect))
        
        pt_lat = round(start_lat + (d_north * meters_to_lat), 6)
        pt_lon = round(start_lon + (d_east * meters_to_lon), 6)
        path_points.append([pt_lon, pt_lat])

    # Runout width expands down the fan
    apex_width_m = 25.0
    toe_width_m = min(220.0, apex_width_m + (runout_length_m * 0.18))
    affected_area_m2 = round((apex_width_m + toe_width_m) * 0.5 * runout_length_m, 1)

    # Hazard classification
    if runout_length_m > 800.0 or slope_deg > 38.0:
        hazard_class = "EXTREME"
    elif runout_length_m > 400.0 or slope_deg > 28.0:
        hazard_class = "HIGH"
    elif runout_length_m > 200.0:
        hazard_class = "MODERATE"
    else:
        hazard_class = "LOW"

    return {
        "start_elevation_m": round(elevation_m, 1),
        "estimated_toe_elevation_m": round(elevation_m - fall_height_m, 1),
        "fall_height_m": round(fall_height_m, 1),
        "slope_gradient_deg": round(slope_deg, 1),
        "aspect_deg": round(aspect_deg, 1),
        "flow_direction_deg": round(aspect_deg, 1),
        "fahrboschung_angle_deg": round(runout_angle_deg, 1),
        "max_runout_length_m": round(runout_length_m, 1),
        "toe_width_m": round(toe_width_m, 1),
        "affected_area_m2": affected_area_m2,
        "runout_hazard_class": hazard_class,
        "estimated_volume_m3": round(vol_clamped, 0),
        "downslope_flowline_geojson": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": path_points,
            },
            "properties": {
                "runout_length_m": round(runout_length_m, 1),
                "hazard_class": hazard_class,
            },
        },
        "runout_corridor_polygon_geojson": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    path_points[0],
                    path_points[2],
                    path_points[-1],
                    path_points[-2],
                    path_points[0],
                ]],
            },
            "properties": {
                "area_m2": affected_area_m2,
                "hazard_class": hazard_class,
            },
        },
        "disclaimer": "AI-generated estimate — requires verification. Not an evacuation contour.",
    }
