"""Demo seed for the three pilot districts.

EVERY value here is either (a) live-derived at seed time from a real DEM/weather
API with provenance recorded, or (b) an explicitly SIMULATED demonstration
assignment. District envelopes are approximate and are labelled as such in the
API and UI; they are not authoritative administrative boundaries.
"""

from __future__ import annotations

import logging
import math
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .domain import ALERT_DISCLAIMER, Role
from .engine import params as P
from .engine.validation import run_validation
from .models import (
    AlertPolicy,
    DataSource,
    District,
    DistrictRainfallThreshold,
    EmergencyFacility,
    FeatureFlag,
    FieldTeam,
    IngestionRun,
    InfrastructureAsset,
    LandslideIncident,
    ModelEvaluation,
    ModelVersion,
    Report,
    Road,
    RoadSegment,
    RoleRow,
    SpatialUnit,
    User,
    UserScope,
)
from .security import hash_password
from .services.ingestion import TERRAIN_SOURCE, WEATHER_SOURCE, OpenMeteoElevationAdapter
from .services.util import iso

log = logging.getLogger("bhushakti.seed")

DEMO_PASSWORD = "BhuShakti#2026"
GRID_STEP = 0.055
TERRAIN_SAMPLE_OFFSET = 0.0025  # ~275 m; finer gradients resolve hill slopes better

DISTRICTS = [
    {
        "code": "AS-KMR",
        "name": "Kamrup Metropolitan",
        "state": "Assam",
        "state_code": "AS",
        "lat": 26.1433,
        "lon": 91.7720,
        "bbox": {"min_lat": 26.00, "max_lat": 26.22, "min_lon": 91.62, "max_lon": 91.92},
        "population_estimate": 1_260_000,
        "geology": "granite_gneiss",
        "elevation_base": 120.0,
        "elevation_amplitude": 260.0,
    },
    {
        "code": "ML-EKH",
        "name": "East Khasi Hills",
        "state": "Meghalaya",
        "state_code": "ML",
        "lat": 25.5300,
        "lon": 91.9000,
        "bbox": {"min_lat": 25.30, "max_lat": 25.65, "min_lon": 91.55, "max_lon": 92.05},
        "population_estimate": 825_000,
        "geology": "schist_phyllite",
        "elevation_base": 1100.0,
        "elevation_amplitude": 650.0,
    },
    {
        "code": "MZ-AIZ",
        "name": "Aizawl",
        "state": "Mizoram",
        "state_code": "MZ",
        "lat": 23.7300,
        "lon": 92.7200,
        "bbox": {"min_lat": 23.60, "max_lat": 23.95, "min_lon": 92.55, "max_lon": 92.95},
        "population_estimate": 400_000,
        "geology": "barail_sandstone",
        "elevation_base": 700.0,
        "elevation_amplitude": 600.0,
    },
]

ROADS = [
    ("AS-KMR", "NH-27", "NH-27 (indicative corridor)", "National Highway",
     [(91.63, 26.02), (91.70, 26.06), (91.76, 26.11), (91.82, 26.15), (91.90, 26.18)]),
    ("AS-KMR", "GSR", "GS Road (indicative corridor)", "Arterial",
     [(91.68, 26.09), (91.74, 26.12), (91.80, 26.16)]),
    ("ML-EKH", "NH-6", "NH-6 (indicative corridor)", "National Highway",
     [(91.58, 25.32), (91.66, 25.40), (91.76, 25.47), (91.86, 25.53), (91.98, 25.58)]),
    ("ML-EKH", "SH-5", "Shillong–Mawkynrew (indicative corridor)", "State Highway",
     [(91.90, 25.55), (92.00, 25.50), (92.04, 25.45)]),
    ("MZ-AIZ", "NH-306", "NH-306 (indicative corridor)", "National Highway",
     [(92.60, 23.68), (92.67, 23.72), (92.74, 23.75), (92.84, 23.79)]),
    ("MZ-AIZ", "AIZ-DUR", "Aizawl–Durtlang (indicative corridor)", "Urban arterial",
     [(92.72, 23.74), (92.76, 23.79), (92.80, 23.84)]),
]

ASSETS = [
    ("AS-KMR", "hospital", "Guwahati Medical College & Hospital (reference location)", 26.1480, 91.7620, 1000, None),
    ("AS-KMR", "hospital", "Community Health Centre — Narengi (demo seed)", 26.1700, 91.8300, 30, None),
    ("AS-KMR", "school", "Government Higher Secondary School — Basistha (demo seed)", 26.1000, 91.7800, None, None),
    ("AS-KMR", "bridge", "Bridge over Bharalu (demo seed)", 26.1200, 91.7900, None, None),
    ("AS-KMR", "settlements", "Kamakhya (approximate)", 26.1660, 91.7050, None, 12000),
    ("AS-KMR", "settlements", "Narengi (approximate)", 26.1720, 91.8350, None, 22000),
    ("AS-KMR", "settlements", "Basistha (approximate)", 26.1000, 91.7800, None, 15000),
    ("AS-KMR", "settlements", "Khanapara (approximate)", 26.1200, 91.8150, None, 30000),
    ("ML-EKH", "hospital", "NEIGRIHMS (reference location)", 25.5640, 91.9150, 500, None),
    ("ML-EKH", "hospital", "Civil Hospital Shillong (reference location)", 25.5700, 91.8830, 300, None),
    ("ML-EKH", "school", "St. Edmund's College (reference location)", 25.5660, 91.8940, None, None),
    ("ML-EKH", "bridge", "Umiam bridge (demo seed)", 25.6600, 91.8800, None, None),
    ("ML-EKH", "settlements", "Mawprem (approximate)", 25.5200, 91.8500, None, 8000),
    ("ML-EKH", "settlements", "Nongthymmai (approximate)", 25.5600, 91.9050, None, 25000),
    ("ML-EKH", "settlements", "Laitumkhrah (approximate)", 25.5730, 91.9010, None, 18000),
    ("ML-EKH", "settlements", "Pynthorumkhrah (approximate)", 25.5820, 91.9200, None, 16000),
    ("MZ-AIZ", "hospital", "Civil Hospital Aizawl (reference location)", 23.7300, 92.7180, 300, None),
    ("MZ-AIZ", "school", "Govt. Higher Secondary School — Chanmari (demo seed)", 23.7280, 92.7140, None, None),
    ("MZ-AIZ", "bridge", "Tlawng bridge (demo seed)", 23.9000, 92.6500, None, None),
    ("MZ-AIZ", "settlements", "Chanmari (approximate)", 23.7280, 92.7130, None, 12000),
    ("MZ-AIZ", "settlements", "Bawngkawn (approximate)", 23.7600, 92.7350, None, 14000),
    ("MZ-AIZ", "settlements", "Durtlang (approximate)", 23.7800, 92.7500, None, 10000),
    ("MZ-AIZ", "settlements", "Sairang (approximate)", 23.8100, 92.6600, None, 6000),
]

DATA_SOURCES = [
    dict(
        id=WEATHER_SOURCE, name="Open-Meteo hourly precipitation", category="Rainfall",
        provider="Open-Meteo (ECMWF IFS / ICON model output)", licence="CC BY 4.0",
        attribution="Weather data by Open-Meteo.com (CC BY 4.0)",
        spatial_resolution="~9-11 km model grid point", temporal_resolution="Hourly, 4-day history / 3-day forecast",
        expected_refresh_min=60, freshness_sla_min=180, fallback_source="sim-rainfall",
        notes="Used as the live rainfall input for the pilot. It is model output, not a rain-gauge observation.",
        coverage="Pilot districts (nearest grid point to district centre)",
    ),
    dict(
        id="open-meteo-soil", name="Open-Meteo soil moisture (0-7 cm)", category="Soil moisture",
        provider="Open-Meteo", licence="CC BY 4.0", attribution="Weather data by Open-Meteo.com (CC BY 4.0)",
        spatial_resolution="~9-11 km model grid point", temporal_resolution="Hourly",
        expected_refresh_min=60, freshness_sla_min=180, fallback_source=None,
        notes="Volumetric soil moisture converted from m3/m3 to percent. Model output, not an in-situ sensor.",
        coverage="Pilot districts",
    ),
    dict(
        id=TERRAIN_SOURCE, name="Copernicus DEM GLO-90 elevation sampling", category="Terrain",
        provider="Copernicus DEM via Open-Meteo elevation API", licence="Copernicus DEM licence (open, attribution)",
        attribution="Copernicus DEM GLO-90 © ESA / European Union",
        spatial_resolution="90 m source, sampled at ~660 m spacing for slope", temporal_resolution="Static (annual refresh)",
        expected_refresh_min=525600, freshness_sla_min=1051200, fallback_source=None,
        notes="Slope, aspect, curvature and ruggedness derived from DEM samples. Slope is a regional approximation at the sampling spacing, not a 90 m slope grid.",
        coverage="Pilot districts",
    ),
    dict(
        id="sim-rainfall", name="Demonstration rainfall generator", category="Rainfall",
        provider="BHUSHAKTI AI (synthetic)", licence="Internal demonstration data",
        attribution="Synthetic — not an observation", spatial_resolution="District",
        temporal_resolution="Hourly snapshot", expected_refresh_min=60, freshness_sla_min=180, fallback_source=None,
        notes="Only used when no live feed is available, and always displayed as SIMULATED.",
        coverage="Pilot districts",
    ),
    dict(
        id="imd-rainfall", name="IMD rainfall (gauge / gridded)", category="Rainfall",
        provider="India Meteorological Department", licence="Restricted — requires a data-sharing agreement",
        attribution="India Meteorological Department", spatial_resolution="Station / 0.25 deg gridded",
        temporal_resolution="Hourly to daily", expected_refresh_min=60, freshness_sla_min=180,
        fallback_source=WEATHER_SOURCE, enabled=False,
        notes="Adapter not implemented: no API credentials or agreement in this environment. Not used for any displayed value.",
        coverage="None",
    ),
    dict(
        id="gpm-imerg", name="NASA GPM IMERG precipitation", category="Rainfall",
        provider="NASA GES DISC", licence="Open, attribution required", attribution="NASA GPM IMERG",
        spatial_resolution="0.1 deg", temporal_resolution="30 min / daily", expected_refresh_min=180,
        freshness_sla_min=720, fallback_source=WEATHER_SOURCE, enabled=False,
        notes="Requires an Earthdata login. Adapter planned; no live connection here.",
        coverage="None",
    ),
    dict(
        id="era5-land", name="ERA5-Land reanalysis", category="Rainfall / soil moisture",
        provider="Copernicus Climate Data Store", licence="Copernicus licence (open, attribution)",
        attribution="Copernicus Climate Change Service", spatial_resolution="0.1 deg", temporal_resolution="Hourly",
        expected_refresh_min=1440, freshness_sla_min=4320, fallback_source=None, enabled=False,
        notes="Best long-term antecedent series. Requires CDS API key; not connected.",
        coverage="None",
    ),
    dict(
        id="gsi-inventory", name="GSI landslide inventory", category="Historical landslides",
        provider="Geological Survey of India", licence="Restricted — institutional access",
        attribution="Geological Survey of India", spatial_resolution="Event point", temporal_resolution="Event",
        expected_refresh_min=10080, freshness_sla_min=43200, fallback_source=None, enabled=False,
        notes="No inventory supplied. Until a verified inventory is loaded the model stays uncalibrated and validation shows VALIDATION IN PROGRESS.",
        coverage="None",
    ),
    dict(
        id="esa-worldcover", name="ESA WorldCover 2021", category="Land cover",
        provider="ESA", licence="CC BY 4.0", attribution="ESA WorldCover project",
        spatial_resolution="10 m", temporal_resolution="Annual", expected_refresh_min=525600,
        freshness_sla_min=1051200, fallback_source=None, enabled=False,
        notes="Not ingested. Zone land-cover values in this build are demo assignments and are labelled SIMULATED.",
        coverage="None",
    ),
    dict(
        id="osm-roads", name="OpenStreetMap road network", category="Exposure",
        provider="OpenStreetMap contributors / Geofabrik", licence="ODbL 1.0",
        attribution="© OpenStreetMap contributors", spatial_resolution="Vector", temporal_resolution="Weekly",
        expected_refresh_min=10080, freshness_sla_min=20160, fallback_source=None, enabled=False,
        notes="Not ingested. Road corridors in this build are indicative demo geometry, not OSM centrelines.",
        coverage="None",
    ),
    dict(
        id="demo-exposure", name="Demonstration exposure assets", category="Exposure",
        provider="BHUSHAKTI AI (synthetic)", licence="Internal demonstration data",
        attribution="Synthetic — approximate locations and estimated populations",
        spatial_resolution="Point", temporal_resolution="Static", expected_refresh_min=525600,
        freshness_sla_min=1051200, fallback_source=None,
        notes="Approximate locality points with estimated populations for interface demonstration only.",
        coverage="Pilot districts",
    ),
    dict(
        id="gridded-population", name="WorldPop gridded population", category="Exposure / population",
        provider="WorldPop (University of Southampton)", licence="CC BY 4.0",
        attribution="WorldPop", spatial_resolution="100 m", temporal_resolution="Annual",
        expected_refresh_min=525600, freshness_sla_min=1051200, fallback_source=None, enabled=False,
        notes="Not ingested; population figures shown are demo estimates.",
        coverage="None",
    ),
    dict(
        id="sentinel-1", name="Sentinel-1 SAR (InSAR readiness)", category="Satellite",
        provider="ESA Copernicus", licence="Open, attribution required", attribution="Copernicus Sentinel data",
        spatial_resolution="~10 m", temporal_resolution="6-12 day revisit", expected_refresh_min=10080,
        freshness_sla_min=20160, fallback_source=None, enabled=False,
        notes="P2 roadmap: InSAR deformation monitoring. No imagery pipeline in this build.",
        coverage="None",
    ),
]

USERS = [
    ("admin@bhushakti.demo", "Platform Administrator", Role.PLATFORM_ADMIN, []),
    ("state.assam@bhushakti.demo", "Assam State Authority", Role.STATE_ADMIN, []),
    ("dc.kamrup@bhushakti.demo", "District Collector — Kamrup Metro", Role.DISTRICT_ADMIN, ["AS-KMR"]),
    ("analyst@bhushakti.demo", "Duty Analyst", Role.ANALYST, ["AS-KMR", "ML-EKH", "MZ-AIZ"]),
    ("field.officer@bhushakti.demo", "Field Officer — Kamrup Metro", Role.FIELD_OFFICER, ["AS-KMR"]),
    ("citizen@bhushakti.demo", "Citizen Demo User", Role.CITIZEN, []),
    ("researcher@bhushakti.demo", "Research Partner", Role.RESEARCHER, []),
]

FEATURE_FLAGS = [
    ("scenario_lab", True, "Isolated what-if analysis for authorised planners."),
    ("low_bandwidth_mode", True, "Text-first, tile-light operational mode."),
    ("public_citizen_alerts", True, "Expose approved alerts on the citizen portal."),
    ("image_ai", False, "Image-assisted hazard indication. Never automatically confirms a landslide."),
    ("sms_delivery", False, "DLT-registered SMS adapter. Disabled: no provider configured."),
    ("email_delivery", False, "Email adapter. Disabled: no provider configured."),
    ("vector_tiles", False, "Server-rendered vector tiles. Not implemented; GeoJSON is served with bbox filtering."),
    ("llm_alert_drafting", False, "LLM-assisted drafting. Never allowed to alter hazard probability or publish."),
]


def _polygon(bbox: dict) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [bbox["min_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["min_lat"]],
        ]],
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _create_roles(db: Session) -> None:
    labels = {
        Role.PLATFORM_ADMIN: "Platform Administrator",
        Role.STATE_ADMIN: "State Administrator",
        Role.DISTRICT_ADMIN: "District Administrator",
        Role.ANALYST: "Authority Analyst",
        Role.FIELD_OFFICER: "Field Officer",
        Role.CITIZEN: "Citizen",
        Role.RESEARCHER: "Researcher",
    }
    for code, name in labels.items():
        if db.get(RoleRow, code) is None:
            db.add(RoleRow(code=code, name=name, description=f"{name} role"))
    db.flush()


def _synthetic_terrain(district: dict, lat: float, lon: float, rng: random.Random) -> tuple[float, float, float, float, float, float]:
    rel_lat = (lat - district["lat"]) * 110
    rel_lon = (lon - district["lon"]) * 100
    elevation = (
        district["elevation_base"]
        + district["elevation_amplitude"] * (0.5 + 0.5 * math.sin(rel_lat * 1.3) * math.cos(rel_lon * 1.1))
        + rng.uniform(-40, 40)
    )
    slope = max(2.0, min(42.0, 14 + 0.35 * district["elevation_amplitude"] / 10 + rng.uniform(-8, 12)))
    aspect = rng.uniform(0, 360)
    curvature = rng.uniform(-0.6, 0.6)
    ruggedness = rng.uniform(20, 140)
    twi = 7.0 + rng.uniform(-1.5, 2.0)
    return elevation, slope, aspect, curvature, ruggedness, twi


def _terrain_from_samples(center: float | None, north: float | None, south: float | None,
                          east: float | None, west: float | None, lat: float) -> dict | None:
    if None in (center, north, south, east, west):
        return None
    dx = TERRAIN_SAMPLE_OFFSET * 111_320 * math.cos(math.radians(lat))
    dy = TERRAIN_SAMPLE_OFFSET * 110_540
    dzdx = (east - west) / (2 * dx)
    dzdy = (north - south) / (2 * dy)
    gradient = math.hypot(dzdx, dzdy)
    slope = math.degrees(math.atan(gradient))
    aspect = (math.degrees(math.atan2(-dzdx, -dzdy)) + 360) % 360
    lap = (north + south + east + west - 4 * center)
    denom = abs(north - center) + abs(south - center) + abs(east - center) + abs(west - center)
    curvature = lap / denom if denom > 1e-6 else 0.0
    ruggedness = max(center, north, south, east, west) - min(center, north, south, east, west)
    tan_beta = math.tan(math.radians(max(0.5, slope)))
    twi = max(3.0, min(14.0, math.log(500.0 / tan_beta)))
    return {
        "elevation_m": round(center, 1),
        "slope_deg": round(slope, 2),
        "aspect_deg": round(aspect, 1),
        "curvature": round(curvature, 3),
        "terrain_ruggedness": round(ruggedness, 1),
        "twi": round(twi, 2),
    }


def _landcover_for(slope: float, elevation: float) -> str:
    if slope >= 32:
        return "bare_or_sparse"
    if elevation >= 1200:
        return "forest"
    if elevation <= 300:
        return "agriculture"
    return "shrub"


def seed_database(db: Session, *, with_network: bool = True, request_id: str = "seed") -> dict:
    if db.execute(select(District)).scalars().first() is not None:
        return {"seeded": False, "reason": "database already contains districts"}

    _create_roles(db)

    # ---- districts
    districts: dict[str, District] = {}
    for spec in DISTRICTS:
        district = District(
            code=spec["code"], name=spec["name"], state=spec["state"], state_code=spec["state_code"],
            lat=spec["lat"], lon=spec["lon"], bbox_json=spec["bbox"], geometry=_polygon(spec["bbox"]),
            boundary_source="Approximate pilot envelope (generated)",
            boundary_note=(
                "Rectangular envelope generated for the pilot — NOT an authoritative district boundary. "
                "Replace with Survey of India / DataMeet boundaries before operational use."
            ),
            population_estimate=spec["population_estimate"],
        )
        db.add(district)
        districts[spec["code"]] = district
    db.flush()

    # ---- zone grid (planning)
    zone_specs: list[dict] = []
    for spec in DISTRICTS:
        bbox = spec["bbox"]
        lat = bbox["min_lat"]
        row = 0
        while lat + GRID_STEP <= bbox["max_lat"] + 1e-9:
            lon = bbox["min_lon"]
            col = 0
            while lon + GRID_STEP <= bbox["max_lon"] + 1e-9:
                center_lat = round(lat + GRID_STEP / 2, 5)
                center_lon = round(lon + GRID_STEP / 2, 5)
                zone_specs.append({
                    "district": spec,
                    "code": f"{spec['code']}-Z{row:02d}{col:02d}",
                    "name": f"{spec['name']} unit {row:02d}{col:02d}",
                    "lat": center_lat,
                    "lon": center_lon,
                    "bbox": {
                        "min_lat": round(lat, 5), "max_lat": round(lat + GRID_STEP, 5),
                        "min_lon": round(lon, 5), "max_lon": round(lon + GRID_STEP, 5),
                    },
                })
                col += 1
                lon += GRID_STEP
            row += 1
            lat += GRID_STEP

    # ---- terrain sampling (real DEM when reachable)
    terrain_source = "Synthetic terrain (network unavailable at seed time)"
    dem_points = 0
    sampled: list[dict | None] = [None] * len(zone_specs)
    if with_network and settings.ingestion_enabled:
        coords: list[tuple[float, float]] = []
        for index, zone in enumerate(zone_specs):
            coords.append((zone["lat"], zone["lon"]))
            sampled[index] = {"center_index": len(coords) - 1}
            for dlat, dlon in ((TERRAIN_SAMPLE_OFFSET, 0), (-TERRAIN_SAMPLE_OFFSET, 0),
                               (0, TERRAIN_SAMPLE_OFFSET), (0, -TERRAIN_SAMPLE_OFFSET)):
                coords.append((round(zone["lat"] + dlat, 5), round(zone["lon"] + dlon, 5)))
            sampled[index].update({
                "north_index": len(coords) - 4, "south_index": len(coords) - 3,
                "east_index": len(coords) - 2, "west_index": len(coords) - 1,
            })
        try:
            elevations = OpenMeteoElevationAdapter().fetch(coords)
            for index, zone in enumerate(zone_specs):
                idx = sampled[index]
                metrics = _terrain_from_samples(
                    elevations[idx["center_index"]], elevations[idx["north_index"]],
                    elevations[idx["south_index"]], elevations[idx["east_index"]],
                    elevations[idx["west_index"]], zone["lat"],
                )
                if metrics:
                    zone["terrain"] = {**metrics, "source": "DEM-derived (live) — Copernicus DEM GLO-90 via Open-Meteo, sampled ~660 m"}
            if any(z.get("terrain") for z in zone_specs):
                terrain_source = "DEM-derived (live) — Copernicus DEM GLO-90 via Open-Meteo"
                dem_points = len(coords)
            log.info("sampled %s DEM points for %s zones", len(coords), len(zone_specs))
        except Exception as exc:  # noqa: BLE001 - seed must still succeed
            log.warning("DEM sampling failed; using synthetic terrain: %s", exc)

    for zone in zone_specs:
        rng = random.Random(hashlib_seed(zone["code"]))
        if not zone.get("terrain"):
            elevation, slope, aspect, curvature, ruggedness, twi = _synthetic_terrain(
                zone["district"], zone["lat"], zone["lon"], rng)
            zone["terrain"] = {
                "elevation_m": round(elevation, 1), "slope_deg": round(slope, 2),
                "aspect_deg": round(aspect, 1), "curvature": round(curvature, 3),
                "terrain_ruggedness": round(ruggedness, 1), "twi": round(twi, 2),
                "source": terrain_source,
            }

    # ---- roads (indicative corridors) then zones with road-cut proximity
    road_rows: list[Road] = []
    for district_code, ref, name, road_class, coords in ROADS:
        road = Road(
            ref=ref, name=name, road_class=road_class, district_codes=[district_code],
            geometry={"type": "LineString", "coordinates": [[lon, lat] for lon, lat in coords]},
            source="Indicative corridor generated for the pilot",
            geometry_note=(
                "Indicative straight-line corridor between approximate waypoints. NOT an authoritative "
                "road centreline; replace with OSM/NHAI geometry before operational use."
            ),
        )
        db.add(road)
        road_rows.append(road)
    db.flush()

    road_points = [(lat, lon) for _, _, _, _, coords in ROADS for lon, lat in coords]
    zone_rows: list[SpatialUnit] = []
    for zone in zone_specs:
        terrain = zone["terrain"]
        bbox = zone["bbox"]
        nearest_road_m = min(
            _haversine_km(zone["lat"], zone["lon"], lat, lon) * 1000.0 for lat, lon in road_points
        )
        area = (GRID_STEP * 111.32) * (GRID_STEP * 111.32 * math.cos(math.radians(zone["lat"])))
        unit = SpatialUnit(
            code=zone["code"],
            district_code=zone["district"]["code"],
            kind="grid_cell",
            name=zone["name"],
            geometry={"type": "Polygon", "coordinates": [[
                [bbox["min_lon"], bbox["min_lat"]], [bbox["max_lon"], bbox["min_lat"]],
                [bbox["max_lon"], bbox["max_lat"]], [bbox["min_lon"], bbox["max_lat"]],
                [bbox["min_lon"], bbox["min_lat"]],
            ]]},
            bbox_json=bbox,
            centroid_lat=zone["lat"],
            centroid_lon=zone["lon"],
            area_km2=round(area, 2),
            elevation_m=terrain["elevation_m"],
            slope_deg=terrain["slope_deg"],
            aspect_deg=terrain["aspect_deg"],
            curvature=terrain["curvature"],
            terrain_ruggedness=terrain["terrain_ruggedness"],
            twi=terrain["twi"],
            landcover=_landcover_for(terrain["slope_deg"], terrain["elevation_m"]),
            geology=zone["district"]["geology"],
            road_cut_proximity_m=round(nearest_road_m, 1),
            terrain_source=terrain["source"],
            landcover_source="Demo assignment (SIMULATED) — ESA WorldCover not ingested",
            geology_source="Demo assignment (SIMULATED) — GSI lithology not ingested",
        )
        db.add(unit)
        zone_rows.append(unit)
    db.flush()

    # ---- road segments assigned to nearest unit
    for road, (district_code, _, _, _, coords) in zip(road_rows, ROADS):
        for i in range(len(coords) - 1):
            (lon1, lat1), (lon2, lat2) = coords[i], coords[i + 1]
            mid_lat, mid_lon = (lat1 + lat2) / 2, (lon1 + lon2) / 2
            best = min(
                ((_haversine_km(mid_lat, mid_lon, z.centroid_lat, z.centroid_lon), z) for z in zone_rows
                 if z.district_code == district_code),
                key=lambda item: item[0],
                default=None,
            )
            if best is None or best[0] > 20:
                continue
            db.add(RoadSegment(
                road_id=road.id,
                zone_id=best[1].id,
                name=f"{road.name} — segment {i + 1}",
                length_km=round(_haversine_km(lat1, lon1, lat2, lon2), 2),
                status="OPEN",
                status_source="MODEL_ESTIMATED",
                evidence="Initial status from model risk; no officer inspection recorded.",
                model_risk_level=None,
            ))
    db.flush()

    # ---- exposure assets
    for district_code, kind, name, lat, lon, capacity, population in ASSETS:
        db.add(InfrastructureAsset(
            kind=kind, name=name, lat=lat, lon=lon, district_code=district_code,
            capacity=capacity, population_estimate=population,
            source="Demo seed — approximate location and / or estimate",
            source_state="SIMULATED",
        ))
    db.flush()

    # ---- synthetic historical inventory (clearly labelled)
    for district_code, spec in [(d["code"], d) for d in DISTRICTS]:
        zones = [z for z in zone_rows if z.district_code == district_code]
        rng = random.Random(hashlib_seed(f"inventory:{district_code}"))
        for i in range(5):
            zone = rng.choice(zones)
            occurred = date(2023 + (i % 3), 6 + (i % 4), 5 + (i * 3) % 22)
            db.add(LandslideIncident(
                district_code=district_code,
                zone_id=zone.id,
                occurred_on=occurred,
                date_uncertainty_days=2,
                lat=zone.centroid_lat + rng.uniform(-0.01, 0.01),
                lon=zone.centroid_lon + rng.uniform(-0.01, 0.01),
                location_accuracy_m=750,
                verified=False,
                source="SIMULATED demonstration inventory — not a verified record",
                description="Synthetic event used to exercise the interface and pipeline. Not evidence of model skill.",
            ))
    db.flush()

    # ---- registry, users, policies, models
    for item in DATA_SOURCES:
        if db.get(DataSource, item["id"]) is None:
            db.add(DataSource(state="UNAVAILABLE", **item))
    db.flush()
    now_utc = datetime.now(timezone.utc)
    terrain = db.get(DataSource, TERRAIN_SOURCE)
    if terrain is not None and "DEM-derived (live)" in terrain_source:
        terrain.state = "LIVE"
        terrain.last_success_at = now_utc
        terrain.last_attempt_at = now_utc
        terrain.last_error = None
        db.add(IngestionRun(source_id=TERRAIN_SOURCE, status="SUCCESS", records=dem_points,
                            message=f"DEM sampled at {dem_points} points for {len(zone_specs)} units"))
    exposure_source = db.get(DataSource, "demo-exposure")
    if exposure_source is not None:
        exposure_source.state = "SIMULATED"
        exposure_source.last_success_at = now_utc
        exposure_source.last_attempt_at = now_utc

    for email, name, role, scopes in USERS:
        user = User(email=email, name=name, role_code=role.value,
                    password_hash=hash_password(DEMO_PASSWORD), is_active=True)
        db.add(user)
        db.flush()
        for scope in scopes:
            db.add(UserScope(user_id=user.id, district_code=scope))

    db.add(AlertPolicy(
        version="policy-v0.1", name="Prototype pilot policy (demonstration)",
        thresholds={"WATCH": 30, "WARNING": 60, "CRITICAL": 80},
        hysteresis_points=5.0, min_duration_min=0, dedupe_window_min=180, active=True, created_by=None,
    ))
    db.add(AlertPolicy(
        version="policy-v1.0-proposed", name="Proposed operational policy (not active)",
        thresholds={"WATCH": 30, "WARNING": 60, "CRITICAL": 80},
        hysteresis_points=5.0, min_duration_min=30, dedupe_window_min=180, active=False, created_by=None,
    ))
    for key, enabled, description in FEATURE_FLAGS:
        db.add(FeatureFlag(key=key, enabled=enabled, description=description, updated_by="seed"))

    validation = run_validation(
        records=[{"label": 1 if i % 4 == 0 else 0, "score": 50 + (i % 50), "lat": 25.5, "lon": 91.9}
                 for i in range(120)],
        method="SPATIAL_BLOCK_CV",
        inventory_is_synthetic=True,
        model_trained=False,
        model_calibrated=False,
    )
    card = {
        "intended_use": (
            "Decision support for prioritising field inspection and authority review across the three pilot "
            "districts. Not for public warning issuance without human approval."
        ),
        "not_intended_for": "Individual-event prediction, evacuation orders, insurance or legal decisions.",
        "training_dataset": "None. Expert-set prototype coefficients; no verified inventory is available.",
        "validation": validation,
        "limitations": [
            "Hazard is an uncalibrated index, not a probability.",
            "Rainfall and soil moisture are model grid-point values, not rain-gauge observations.",
            "Land cover and geology are demonstration assignments.",
            "Prediction units are ~34 km2 grid cells, not slope units.",
            "No down-slope runout or InSAR deformation is modelled.",
            "District envelopes and road corridors are approximate.",
        ],
        "release_date": None,
        "owner": "BHUSHAKTI AI pilot team",
    }
    model = ModelVersion(
        version=P.MODEL_VERSION, kind="HYBRID_LOGISTIC_HEURISTIC",
        name="Susceptibility logistic baseline + rainfall ID trigger",
        features=[f.key for f in P.FEATURES] + ["rainfall_1h", "rainfall_6h", "rainfall_24h",
                                                "rainfall_72h", "soil_moisture_pct", "forecast_24h"],
        training_period="none",
        spatial_coverage="Three pilot districts (approximate envelopes)",
        validation_approach=(
            "Spatial block cross-validation and temporal hold-out are implemented, but no verified "
            "inventory and no fitted model exist, so no metric may be published."
        ),
        status="PROTOTYPE_ACTIVE", metrics={}, card=card,
        released_at=datetime.now(timezone.utc), changelog="Initial prototype release.",
    )
    db.add(model)
    db.flush()
    db.add(ModelEvaluation(
        model_version=model.version, method="SPATIAL_BLOCK_CV",
        status=validation["status"], metrics={}, notes="; ".join(validation.get("blockers", [])),
    ))

    # ---- a few pending field reports to exercise verification
    rng = random.Random(hashlib_seed("reports"))
    for i, district_code in enumerate([d["code"] for d in DISTRICTS]):
        zones = [z for z in zone_rows if z.district_code == district_code]
        zone = rng.choice(zones)
        db.add(Report(
            client_uuid=f"seed-report-{district_code.lower()}-{i:02d}",
            zone_id=zone.id, district_code=district_code,
            hazard_type=["GROUND_CRACK", "SLOPE_MOVEMENT", "ROAD_BLOCKAGE"][i],
            description="Seeded demonstration report awaiting officer verification.",
            lat=zone.centroid_lat, lon=zone.centroid_lon, gps_accuracy_m=12.0,
            observed_at=datetime.now(timezone.utc) - timedelta(hours=3),
            status="PENDING_VERIFICATION", anonymous=False,
            reporter_name="Demo field officer", consent=True, sync_source="online",
        ))

    # ---- emergency facilities
    FACILITIES = [
        {"district": "AS-KMR", "kind": "HOSPITAL", "name": "Gauhati Medical College Hospital (GMCH)", "lat": 26.155, "lon": 91.776, "capacity": 1200, "occupancy": 840, "phone": "+91 361 2529457", "address": "Bhangagarh, Guwahati, Assam 781032"},
        {"district": "AS-KMR", "kind": "SHELTER", "name": "Khanapara Veterinary College Indoor Shelter", "lat": 26.130, "lon": 91.815, "capacity": 450, "occupancy": 0, "phone": "+91 361 2364973", "address": "Khanapara, Guwahati, Assam 781022"},
        {"district": "AS-KMR", "kind": "SCHOOL_SHELTER", "name": "Dispur Higher Secondary School Shelter", "lat": 26.142, "lon": 91.792, "capacity": 300, "occupancy": 0, "phone": "+91 361 2261900", "address": "Dispur Capital Complex, Guwahati"},
        {"district": "ML-EKH", "kind": "HOSPITAL", "name": "Shillong Civil Hospital", "lat": 25.572, "lon": 91.882, "capacity": 500, "occupancy": 320, "phone": "+91 364 2224100", "address": "Secretariat Hills, Shillong, Meghalaya 793001"},
        {"district": "ML-EKH", "kind": "SHELTER", "name": "JN Sports Complex Indoor Disaster Shelter", "lat": 25.584, "lon": 91.895, "capacity": 600, "occupancy": 0, "phone": "+91 364 2501234", "address": "Polo Grounds, Shillong 793001"},
        {"district": "MZ-AIZ", "kind": "HOSPITAL", "name": "Aizawl Civil Hospital", "lat": 23.727, "lon": 92.717, "capacity": 400, "occupancy": 210, "phone": "+91 389 2322318", "address": "Dawrpui, Aizawl, Mizoram 796001"},
        {"district": "MZ-AIZ", "kind": "SHELTER", "name": "Hawla Indoor Stadium Shelter Complex", "lat": 23.745, "lon": 92.728, "capacity": 550, "occupancy": 0, "phone": "+91 389 2334567", "address": "Republic Veng, Aizawl 796005"},
    ]
    for fac in FACILITIES:
        db.add(EmergencyFacility(
            district_code=fac["district"], kind=fac["kind"], name=fac["name"],
            lat=fac["lat"], lon=fac["lon"], capacity=fac["capacity"], current_occupancy=fac["occupancy"],
            contact_phone=fac["phone"], address=fac["address"], status="OPERATIONAL", verified_by_authority=True,
            power_backup=True, water_supply=True, medical_supplies=True,
        ))

    # ---- field teams
    TEAMS = [
        {"district": "AS-KMR", "code": "AS-RRU-01", "name": "Kamrup Geotechnical Response Unit 1", "lead": "Er. P. B. Sarma", "phone": "+91 94350 11234", "spec": "GEOTECHNICAL_ASSESSMENT", "lat": 26.152, "lon": 91.758, "count": 5},
        {"district": "AS-KMR", "code": "AS-SAR-02", "name": "Guwahati Urban Search & Rescue Brigade", "lead": "Capt. D. Hazarika", "phone": "+91 94350 22345", "spec": "SEARCH_AND_RESCUE", "lat": 26.110, "lon": 91.790, "count": 8},
        {"district": "ML-EKH", "code": "ML-SDRF-01", "name": "East Khasi Hills SDRF Rapid Mountain Team", "lead": "Inspector B. Lyngdoh", "phone": "+91 98630 33456", "spec": "SEARCH_AND_RESCUE", "lat": 25.578, "lon": 91.893, "count": 6},
        {"district": "MZ-AIZ", "code": "MZ-GEO-01", "name": "Aizawl Slope Inspection Cadre", "lead": "Dr. R. Lalrinawma", "phone": "+91 98620 44567", "spec": "GEOTECHNICAL_ASSESSMENT", "lat": 23.730, "lon": 92.717, "count": 4},
    ]
    for tm in TEAMS:
        db.add(FieldTeam(
            district_code=tm["district"], team_code=tm["code"], name=tm["name"],
            leader_name=tm["lead"], leader_phone=tm["phone"], specialization=tm["spec"],
            base_lat=tm["lat"], base_lon=tm["lon"], status="AVAILABLE", member_count=tm["count"],
            current_active_assignments=0, equipment=["Digital inclinometer", "Drone reconnaissance kit", "First-aid medical pack"],
        ))

    # ---- district rainfall thresholds
    THRESHOLDS = [
        {"district": "AS-KMR", "watch": 55.0, "warn": 95.0, "crit": 140.0, "ant": 160.0, "alpha": 12.8, "beta": 0.35, "notes": "Kamrup weathered gneissic red soil baseline"},
        {"district": "ML-EKH", "watch": 85.0, "warn": 145.0, "crit": 210.0, "ant": 280.0, "alpha": 18.2, "beta": 0.42, "notes": "East Khasi Hills heavy monsoon rainfall adaptation"},
        {"district": "MZ-AIZ", "watch": 65.0, "warn": 110.0, "crit": 165.0, "ant": 195.0, "alpha": 14.6, "beta": 0.39, "notes": "Aizawl Surma shale dip-slope bedding threshold"},
    ]
    for th in THRESHOLDS:
        db.add(DistrictRainfallThreshold(
            district_code=th["district"], threshold_24h_watch_mm=th["watch"],
            threshold_24h_warning_mm=th["warn"], threshold_24h_critical_mm=th["crit"],
            antecedent_72h_mm=th["ant"], intensity_alpha=th["alpha"], intensity_beta=th["beta"],
            calibrated_by="Regional Geotechnical Panel (NER-GSI)", validation_status="LOCALLY_CALIBRATED",
            notes=th["notes"],
        ))

    db.commit()
    log.info("seed complete: %s zones, %s roads, %s sources", len(zone_rows), len(road_rows), len(DATA_SOURCES))

    from .services import risk as risk_service  # local import to avoid a cycle

    with_weather = False
    if settings.ingestion_enabled:
        from .services.ingestion import ingest_weather
        try:
            # Always probe the live feed so the registry reflects reality...
            ingest_weather(db, districts=list(districts.values()), mode="live",
                           request_id=request_id, actor_email="seed")
            with_weather = True
            # ...then, in DEMO with replay rainfall, use a labelled simulated monsoon
            # event for assessments so the rainy-season workflow can be demonstrated.
            if settings.demo_mode and settings.demo_rainfall == "replay":
                ingest_weather(db, districts=list(districts.values()), mode="simulated",
                               request_id=request_id, actor_email="seed")
        except Exception as exc:  # noqa: BLE001
            log.warning("weather ingestion during seed failed: %s", exc)
    summary = risk_service.recalculate(
        db, district_codes=list(districts.keys()), actor=None, request_id=request_id,
        reason="Initial assessment after seeding",
    )
    from .seed_all_sections import seed_all_sections
    try:
        seed_all_sections(db)
    except Exception as exc:  # noqa: BLE001
        log.warning("seed_all_sections encountered error: %s", exc)

    return {
        "seeded": True,
        "zones": len(zone_rows),
        "districts": list(districts.keys()),
        "roads": len(road_rows),
        "users": len(USERS),
        "demo_password": DEMO_PASSWORD,
        "terrain_source": terrain_source,
        "weather_ingested": with_weather,
        "initial_risk": {
            "run_id": summary.get("run_id"),
            "zones_assessed": summary.get("zones_assessed"),
            "hazard_distribution": summary.get("hazard_distribution"),
            "alerts": summary.get("alert_candidates_created"),
        },
        "demo_credentials": [u[0] for u in USERS],
    }


def hashlib_seed(value: str) -> int:
    import hashlib

    return int(hashlib.sha256(value.encode()).hexdigest()[:12], 16)
