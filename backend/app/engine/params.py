"""Model parameters — single source of truth, explicitly versioned.

PROVENANCE. Every coefficient below was set by expert judgement to produce a
monotone, physically plausible prototype. They were NOT fitted on a verified
landslide inventory and the resulting score is NOT a calibrated probability.
The API therefore reports ``probability_status = NOT_CALIBRATED`` and
``hazard_probability = null`` until a model trained and calibrated on a real
inventory is released (see ML_METHODOLOGY.md and MODEL_CARD.md).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

MODEL_VERSION = "suscept-v0.1+trigger-v0.1"
SUSCEPTIBILITY_VERSION = "suscept-v0.1"
TRIGGER_VERSION = "trigger-v0.1"
ALERT_POLICY_VERSION = "policy-v0.1"
FIELD_EVIDENCE_VERSION = "field-v0.1"


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    label: str
    unit: str
    reference_mean: float
    reference_scale: float
    weight: float
    provenance: str
    note: str = ""

    def standardise(self, value: float) -> float:
        return (value - self.reference_mean) / self.reference_scale


# Deterministic logistic susceptibility model: z = b0 + Σ w_i * z_i
#
# Reference means/scales are the observed distribution of the 116 pilot units
# (Nov 2026 DEM sampling + demo land-cover/geology assignment). They are used
# only to put features on a comparable scale; they are not fitted coefficients.
# Recompute them when coverage expands beyond the three pilot districts.
REFERENCE_NOTE = "Reference distribution: 116 pilot units, Nov 2026"

FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("slope_deg", "Slope angle", "°", 7.4, 8.5, 0.95,
                "DEM-derived (live)", "Steeper terrain raises susceptibility."),
    FeatureSpec("terrain_ruggedness", "Terrain relief", "m", 85.5, 76.5, 0.45,
                "DEM-derived (live)", "Elevation range across the sampled cell."),
    FeatureSpec("curvature", "Profile curvature", "index", -0.05, 0.66, 0.25,
                "DEM-derived (live)", "Concave hollows accumulate water."),
    FeatureSpec("elevation_m", "Elevation", "m", 818.0, 603.0, 0.15,
                "DEM-derived (live)", "Weak association in NER."),
    FeatureSpec("twi", "Topographic wetness index", "index", 8.26, 1.05, 0.30,
                "DEM-derived proxy (live)", "Approximated from slope; contributing area not modelled."),
    FeatureSpec("aspect_wetness", "Aspect wetness", "-1..1", 0.0, 0.6, 0.25,
                "DEM-derived (live)", "South/south-west aspects receive more monsoon rainfall."),
    FeatureSpec("landcover_factor", "Land cover", "factor 0..1", 0.36, 0.18, 0.60,
                "Demo assignment (SIMULATED)", "Replaced by ESA WorldCover when ingested."),
    FeatureSpec("geology_factor", "Geology", "factor 0..1", 0.46, 0.16, 0.70,
                "Demo assignment (SIMULATED)", "Replaced by GSI lithology when licensed."),
    FeatureSpec("road_cut_factor", "Road-cut proximity", "factor 0..1", 0.05, 0.15, 0.40,
                "Derived from indicative demo corridors", "Cut slopes near roads destabilise hillsides."),
)

INTERCEPT = 0.0

# Caine (1980) global intensity–duration envelope: I = a * D^b  [mm/h, hours].
ID_A = 14.82
ID_B = -0.39
# Regional multiplier for the NER monsoon. PROTOTYPE, not validated for NER.
ID_REGIONAL_FACTOR = 1.35
ID_SOURCE = "Caine (1980) global envelope, scaled by an unvalidated NER factor of 1.35"

TRIGGER_WEIGHTS = {"r_1h": 0.15, "r_6h": 0.25, "r_24h": 0.30, "r_72h": 0.15, "r_fc24": 0.15}
TRIGGER_LOGIT_SCALE = 2.0
SOIL_MOISTURE_FLOOR_PCT = 20.0
SOIL_MOISTURE_CEILING_PCT = 60.0
SOIL_MOISTURE_MAX_BOOST = 0.30
MONSOON_MONTHS = (5, 6, 7, 8, 9, 10)
DRY_SEASON_TRIGGER_FACTOR = 0.85
# Hazard is susceptibility x trigger activation, not an additive sum. Without rain,
# even a highly susceptible slope is not at high *hazard* — it is primed. The floor
# keeps a small residual so "no rain" does not read as literally zero risk.
TRIGGER_FLOOR = 0.20
TRIGGER_UNAVAILABLE_MULTIPLIER = 0.50  # unknown weather -> mid-range assumption, coverage reduced

FIELD_EVIDENCE_MAX_POINTS = 15.0
FIELD_EVIDENCE_HALF_LIFE_DAYS = 7.0
FIELD_EVIDENCE_WINDOW_DAYS = 14
FIELD_EVIDENCE_WEIGHTS = {
    "SLOPE_MOVEMENT": 8.0,
    "DEBRIS_FLOW": 8.0,
    "GROUND_CRACK": 6.0,
    "SUBSIDENCE": 6.0,
    "ROCKFALL": 5.0,
    "ROAD_BLOCKAGE": 3.0,
    "OTHER": 2.0,
}

# Exposure / vulnerability / priority
ZONE_BUFFER_KM = 2.5
EXPOSURE_NORMALISER = 12.0
EXPOSURE_WEIGHTS = {
    "bridges": 1.0,
    "hospitals": 1.0,
    "schools": 0.6,
    "settlements": 0.8,
    "road_km": 0.5,
    "population": 0.002,  # per 1,000 exposed people
}
VULNERABILITY_WEIGHTS = {
    "settlement_density": 0.30,
    "road_dependency": 0.25,
    "emergency_access_gap": 0.20,
    "landcover_sensitivity": 0.15,
    "population_share": 0.10,
}
PRIORITY_WEIGHTS = {"hazard": 0.60, "exposure": 0.25, "vulnerability": 0.15}
# Separate from the hazard bands: a serious hazard with nothing exposed is not P1.
PRIORITY_THRESHOLDS = {"P1": 75.0, "P2": 55.0, "P3": 35.0}

# Coverage scoring — an explicit rule, not a fabricated confidence percentage.
COVERAGE_POINTS = {
    "weather_live_fresh": 3,
    "weather_live_aged": 2,
    "weather_cached": 1,
    "soil_moisture_live": 1,
    "terrain_live": 2,
    "verified_inventory": 1,
    "landcover_authoritative": 1,
}
COVERAGE_HIGH_MIN = 6
COVERAGE_MEDIUM_MIN = 3

FORECAST_HORIZONS = (6, 12, 24, 48)

LANDSLIDE_TYPE_FACTORS = {
    "bare_or_sparse": 0.90,
    "agriculture": 0.40,
    "shrub": 0.50,
    "forest": 0.10,
    "plantation": 0.30,
    "built_up": 0.60,
    "water": 0.0,
    "unknown": 0.35,
}

GEOLOGY_FACTORS = {
    "quaternary_alluvium": 0.05,
    "tertiary_sandstone_shale": 0.55,
    "disang_flysch": 0.85,
    "barail_sandstone": 0.40,
    "granite_gneiss": 0.20,
    "schist_phyllite": 0.60,
    "limestone": 0.30,
    "colluvium": 0.80,
    "unknown": 0.40,
}


@dataclass(frozen=True)
class ModelParams:
    version: str = MODEL_VERSION
    susceptibility_version: str = SUSCEPTIBILITY_VERSION
    trigger_version: str = TRIGGER_VERSION
    field_version: str = FIELD_EVIDENCE_VERSION
    features: tuple[FeatureSpec, ...] = FEATURES
    intercept: float = INTERCEPT
    trained: bool = False
    calibrated: bool = False
    calibration_note: str = (
        "Parameters are expert-set and uncalibrated. Hazard is an index (0-100), not a probability."
    )
    training_dataset: str = "none (prototype expert-set weights)"

    def feature(self, key: str) -> FeatureSpec:
        for f in self.features:
            if f.key == key:
                return f
        raise KeyError(key)

    def documentation(self) -> dict:
        return {
            "version": self.version,
            "trained": self.trained,
            "calibrated": self.calibrated,
            "calibration_note": self.calibration_note,
            "training_dataset": self.training_dataset,
            "intercept": self.intercept,
            "features": [
                {
                    "key": f.key,
                    "label": f.label,
                    "unit": f.unit,
                    "reference_mean": f.reference_mean,
                    "reference_scale": f.reference_scale,
                    "weight": f.weight,
                    "provenance": f.provenance,
                    "note": f.note,
                }
                for f in self.features
            ],
            "trigger": {
                "id_envelope": {"a": ID_A, "b": ID_B, "regional_factor": ID_REGIONAL_FACTOR, "source": ID_SOURCE},
                "weights": TRIGGER_WEIGHTS,
                "monsoon_months": list(MONSOON_MONTHS),
                "combination": "hazard = 100 * (S/100) * (0.20 + 0.80 * T/100)",
                "trigger_unavailable_multiplier": TRIGGER_UNAVAILABLE_MULTIPLIER,
            },
            "field_evidence": {
                "max_points": FIELD_EVIDENCE_MAX_POINTS,
                "half_life_days": FIELD_EVIDENCE_HALF_LIFE_DAYS,
                "weights": FIELD_EVIDENCE_WEIGHTS,
            },
            "exposure": {
                "buffer_km": ZONE_BUFFER_KM,
                "normaliser": EXPOSURE_NORMALISER,
                "weights": EXPOSURE_WEIGHTS,
            },
            "vulnerability": {"weights": VULNERABILITY_WEIGHTS, "note": "Assumption-based, configurable."},
            "priority": {
                "weights": PRIORITY_WEIGHTS,
                "thresholds": PRIORITY_THRESHOLDS,
                "note": "Operational ranking only; independent of hazard probability.",
            },
        }


PARAMS = ModelParams()
