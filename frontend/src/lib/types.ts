export type RiskLevel = "SAFE" | "WATCH" | "WARNING" | "CRITICAL";
export type PriorityLevel = "P1" | "P2" | "P3" | "P4";
export type DataState = "LIVE" | "CACHED" | "STALE" | "DEGRADED" | "UNAVAILABLE" | "SIMULATED";
export type CoverageLevel = "HIGH" | "MEDIUM" | "LOW";

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  role_label: string;
  districts: string[];
  statewide: boolean;
}

export interface ZoneProperties {
  id: number;
  code: string;
  name: string;
  kind: string;
  district_code: string;
  district_name: string;
  state: string;
  centroid: { lat: number; lon: number };
  area_km2: number;
  hazard_index: number | null;
  hazard_level: RiskLevel | null;
  hazard_probability: null;
  probability_status: "NOT_CALIBRATED";
  priority_level: PriorityLevel | null;
  priority_label: string;
  exposure_score: number | null;
  vulnerability_score: number | null;
  coverage_level: CoverageLevel | null;
  susceptibility_index: number | null;
  weather_source_state: DataState | null;
  computed_at: string | null;
  data_age_minutes: number | null;
  out_of_domain: boolean;
  model_version: string;
  terrain: {
    elevation_m: number | null;
    slope_deg: number | null;
    aspect_deg: number | null;
    curvature: number | null;
    ruggedness: number | null;
    twi: number | null;
    landcover: string | null;
    geology: string | null;
  };
}

export interface ZoneFeature {
  type: "Feature";
  geometry: GeoJSON.Polygon;
  properties: ZoneProperties;
}

export interface ZoneCollection {
  type: "FeatureCollection";
  features: ZoneFeature[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
    thresholds: Record<string, number>;
    disclaimer: string;
    generated_at: string;
    scope: string | string[] | null;
  };
}

export interface Driver {
  key: string;
  label: string;
  value: number | string | null;
  log_odds: number | null;
  index_effect: number;
  direction: "increases" | "reduces";
  provenance?: string;
}

export interface Coverage {
  level: CoverageLevel;
  points: number;
  max_points: number;
  reasons: string[];
  out_of_domain: boolean;
  out_of_domain_note: string;
  method: string;
}

export interface TrajectoryPoint {
  horizon_h: number;
  hazard_index: number;
  hazard_level: RiskLevel;
  trigger_index: number;
  forecast_rainfall_mm: number;
  forecast_issued_at: string | null;
  probability_status: string;
  note: string;
}

export interface ZoneDetail extends ZoneProperties {
  district: {
    code: string;
    name: string;
    state: string;
    lat: number;
    lon: number;
    geometry: GeoJSON.Polygon;
    boundary_note: string;
    population_estimate: number | null;
  };
  inputs: {
    rainfall?: Record<string, number | null>;
    soil_moisture_pct?: number | null;
    observed_at?: string | null;
    weather_source_id?: string | null;
    weather_source_state?: DataState;
    forecasts?: Record<string, number>;
    forecast_issued_at?: string | null;
    trigger?: {
      ratios?: Record<string, number | null>;
      combined_ratio?: number;
      thresholds_mm_per_h?: Record<string, number>;
      soil_moisture_factor?: number | null;
      season_factor?: number;
      id_source?: string;
    };
    trigger_notes?: string[];
    static?: { index: number; logit: number; terms: Driver[]; missing: string[]; intercept: number };
    components?: { static_index: number; trigger_index: number; dynamic_lift_points: number; formula: string };
    field_evidence?: { applied_points: number; cap_points: number; raw_points: number; note: string };
    exposure?: {
      score: number;
      counts: Record<string, number>;
      road_km_at_risk: number;
      population_exposed: number | null;
      assets: Array<{ id: number; name: string; kind: string; distance_km: number; population_estimate?: number | null }>;
      method: string;
      notes: string[];
    };
    vulnerability?: {
      score: number;
      components: Record<string, number>;
      weights: Record<string, number>;
      nearest_hospital_km: number | null;
      note: string;
    };
    priority?: {
      score: number;
      level: PriorityLevel;
      label: string;
      weights: Record<string, number>;
      contributions: Record<string, number>;
      formula: string;
      note: string;
    };
    coverage?: Coverage;
    recommended_action?: string;
    verified_inventory_count?: number;
    scenario?: Record<string, unknown> | null;
  };
  drivers: {
    contributions: Driver[];
    top_risk_increasing: Driver[];
    top_risk_reducing: Driver[];
    narrative: string;
    attribution_method: string;
    model_note: string;
  };
  coverage: Coverage | null;
  exposure: NonNullable<ZoneDetail["inputs"]>["exposure"] | null;
  vulnerability: ZoneDetail["inputs"]["vulnerability"] | null;
  priority: ZoneDetail["inputs"]["priority"] | null;
  field_evidence: ZoneDetail["inputs"]["field_evidence"] | null;
  recommended_action: string | null;
  trajectory: {
    points: TrajectoryPoint[];
    missing: Array<{ horizon_h: number; reason: string }>;
    supported_horizons: number[];
    unavailable_horizons: number[];
    method: string;
    probability_status: string;
    forecast_observations?: Array<{ horizon_h: number; rainfall_mm: number }>;
  } | null;
  incidents: Array<{
    id: number;
    occurred_on: string;
    date_uncertainty_days: number;
    distance_km: number;
    location_accuracy_m: number;
    verified: boolean;
    source: string;
    description: string;
  }>;
  reports: Report[];
  road_segments: RoadSegment[];
  history: Array<{
    computed_at: string;
    hazard_index: number;
    hazard_level: RiskLevel;
    priority_level: PriorityLevel;
    coverage_level: CoverageLevel;
  }>;
  open_alerts: Alert[];
  provenance: Record<string, string | null>;
  disclaimer: string;
  thresholds: Record<string, number>;
}

export interface Report {
  id: number;
  client_uuid: string;
  zone_id: number | null;
  district_code: string | null;
  hazard_type: string;
  description: string;
  lat: number | null;
  lon: number | null;
  gps_accuracy_m: number | null;
  observed_at: string;
  status: "PENDING_VERIFICATION" | "VERIFIED" | "REJECTED";
  anonymous: boolean;
  reporter: string | null;
  media_count: number;
  verification_note: string;
  verified_at: string | null;
  risk_adjustment_applied: number;
  sync_source: string;
  created_at: string;
}

export interface RoadSegment {
  id: number;
  road_id: number;
  zone_id: number | null;
  name: string;
  length_km: number;
  status: "OPEN" | "RESTRICTED" | "AT_RISK" | "BLOCKED";
  status_source: "MODEL_ESTIMATED" | "OFFICER_VERIFIED" | "OFFICIAL_CLOSURE";
  status_updated_at: string;
  evidence: string;
  model_risk_level: RiskLevel | null;
}

export interface Alert {
  id: number;
  reference: string;
  zone_id: number;
  zone_name: string | null;
  district_name: string | null;
  state: string | null;
  severity: RiskLevel;
  status: string;
  headline: string;
  reason: string;
  instructions: string;
  onset: string;
  expires: string;
  geometry: GeoJSON.Polygon;
  threatened_assets: Array<{ name: string; kind: string; distance_km?: number }>;
  source: string;
  disclaimer: string;
  template_version: string;
  language: string;
  hazard_index: number;
  priority_level: PriorityLevel;
  policy_version: string;
  is_scenario: boolean;
  created_at: string;
  approved_at: string | null;
  rejection_reason: string | null;
  cancel_reason: string | null;
  deliveries: Array<{
    channel: string;
    language: string;
    status: string;
    detail: string;
    template_version: string;
    delivered_at: string | null;
  }>;
}

export interface Assignment {
  id: number;
  zone_id: number;
  zone_name: string | null;
  district_code: string | null;
  alert_id: number | null;
  title: string;
  priority: PriorityLevel;
  priority_label: string;
  status: string;
  assigned_to: number | null;
  assignee_name: string | null;
  notes: string;
  reason: string;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  hazard_index: number | null;
  hazard_level: RiskLevel | null;
  exposure_score: number | null;
  vulnerability_score: number | null;
  recommended_action: string | null;
}

export interface RiskSummary {
  jurisdiction: { districts: string[]; statewide: boolean };
  kpis: {
    zones: number;
    critical_zones: number;
    warning_zones: number;
    watch_zones: number;
    safe_zones: number;
    active_alerts: number;
    pending_alerts: number;
    roads_at_risk: number;
    roads_blocked: number;
    pending_reports: number;
    population_exposed_estimate: number | null;
  };
  population_note: string;
  hazard_distribution: Record<string, number>;
  coverage_distribution: Record<string, number>;
  thresholds: Record<string, number>;
  probability_status: string;
  last_run: string | null;
  conditions: Array<{
    district_code: string;
    district_name: string;
    state: string | null;
    rainfall_1h: number | null;
    rainfall_24h: number | null;
    rainfall_72h: number | null;
    soil_moisture_pct: number | null;
    observed_at: string | null;
    source_id: string | null;
    source_state: DataState;
    attribution: string | null;
  }>;
  disclaimer: string;
  demo_mode: boolean;
}

export interface DataSource {
  id: string;
  name: string;
  category: string;
  provider: string;
  licence: string;
  attribution: string;
  spatial_resolution: string;
  temporal_resolution: string;
  expected_refresh_min: number;
  freshness_sla_min: number;
  fallback_source: string | null;
  state: DataState;
  last_success_at: string | null;
  last_attempt_at: string | null;
  last_error: string | null;
  enabled: boolean;
  notes: string;
  coverage: string;
  age_minutes: number | null;
}
