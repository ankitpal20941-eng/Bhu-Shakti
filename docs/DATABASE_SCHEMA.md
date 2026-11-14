# Database schema

Development uses SQLite (`backend/data/bhushakti.db`) through SQLAlchemy 2. Production targets
PostgreSQL 16 with PostGIS; the ORM types are portable (numeric/float, JSON, text) and geometry is
stored as GeoJSON in JSON columns with a parallel bbox for filtering. Migrations live in
`backend/migrations` and are applied by the runner in `app/db.py` (a `schema_migrations` table
records applied versions). There is no Alembic wiring in this build.

## 1. Identity and scope

| Table | Purpose | Key columns |
| --- | --- | --- |
| `roles` | Role vocabulary and labels | `code` PK, `label` |
| `users` | Accounts | `id`, `email` unique, `name`, `role_code` FK, `password_hash` (PBKDF2), `is_active`, `last_login_at` |
| `user_scopes` | District grants | `user_id`, `district_code` (unique pair) |
| `districts` | Pilot districts | `code` PK, `name`, `state`, `lat/lon`, `bbox_json`, `geometry` (GeoJSON), `boundary_source`, `boundary_note`, `population_estimate` |

`user_scopes` is authoritative for jurisdiction. Statewide roles (`platform_admin`,
`state_admin`) bypass the scope filter; every other role is restricted in SQL, not in the UI.

## 2. Geography and evidence

| Table | Purpose | Key columns |
| --- | --- | --- |
| `spatial_units` | Risk units (~2 km grid cells) | `id`, `code`, `name`, `district_code`, `centroid_lat/lon`, `area_km2`, `geometry`, `bbox_json`, DEM features (`elevation_m`, `slope_deg`, `aspect_deg`, `curvature`, `ruggedness`, `twi`), `landcover`, `geology` |
| `feature_snapshots` | Frozen inputs per computation | `unit_id`, `payload` JSON, `created_at` |
| `weather_observations` | Rainfall windows | `district_code`, `observed_at`, `rainfall_1h/6h/24h/72h`, `source_id`, `attribution` |
| `weather_forecasts` | Horizons 6/12/24/48 h | `district_code`, `issued_at`, `horizon_h`, `rainfall_mm`, `source_id` |
| `soil_moisture_records` | Soil moisture | `district_code`, `observed_at`, `moisture_pct`, `source_id` |
| `landslide_incidents` | Historical inventory | `occurred_on`, `date_uncertainty_days`, `lat/lon`, `location_accuracy_m`, `verified`, `source`, `description`, `synthetic` |
| `sensors`, `sensor_readings` | Placeholder for in-situ IoT | no devices provisioned |

The inventory in the demo database is **synthetic** (`synthetic = 1`) and is used only to show
history; the validation gate refuses to publish metrics derived from it.

## 3. Risk

| Table | Purpose | Key columns |
| --- | --- | --- |
| `risk_assessments` | One row per unit per run | `unit_id`, `computed_at`, `hazard_index`, `hazard_level`, `hazard_probability` (always NULL), `probability_status`, `static_index`, `trigger_index`, `exposure_score`, `vulnerability_score`, `priority_score`, `priority_level`, `coverage_level`, `coverage_points`, `weather_source_state`, `data_age_minutes`, `out_of_domain`, `field_points`, `model_version`, `inputs` JSON, `drivers` JSON, `is_scenario` |
| `scenario_runs` | Scenario header | `name`, `created_by`, `inputs` JSON, `summary` JSON, `district_codes` JSON, `created_at` |

`risk_assessments` is append-only. The "current" assessment for a unit is the newest row with
`is_scenario = 0`. History charts and the trajectory endpoint read the same rows. The `inputs`
JSON is the audit trail for a score: rainfall windows, source state, trigger ratios, static
terms, coverage reasons, exposure counts, priority contributions and the engine version strings.

Indexes: `(unit_id, computed_at DESC)`, `(district_code)`, `(is_scenario, computed_at)`.

## 4. Reports

| Table | Purpose | Key columns |
| --- | --- | --- |
| `reports` | Field/citizen hazard reports | `client_uuid` unique, `zone_id`, `district_code`, `hazard_type`, `description`, `lat/lon`, `gps_accuracy_m`, `observed_at`, `status`, `anonymous`, `reporter_name`, `verification_note`, `verified_by`, `verified_at`, `risk_adjustment_applied`, `sync_source` |
| `report_media` | Stored files | `report_id`, `storage_key`, `content_type`, `bytes`, `sha256` |

Status transitions: `PENDING_VERIFICATION → VERIFIED | REJECTED`. Re-verification is refused by
the API; the audit log keeps the first decision.

## 5. Exposure and response

| Table | Purpose | Key columns |
| --- | --- | --- |
| `roads` | Road corridors | `ref`, `name`, `district_code` |
| `road_segments` | Segment status | `road_id`, `zone_id`, `name`, `length_km`, `status`, `status_source`, `status_updated_at`, `evidence` |
| `infrastructure_assets` | Bridges, hospitals, schools, settlements | `kind`, `name`, `lat/lon`, `district_code`, `population_estimate`, `source` |
| `response_assignments` | Incident lifecycle | `zone_id`, `alert_id`, `title`, `priority`, `status`, `assigned_to`, `notes`, `reason`, `due_at`, `closed_at` |
| `alerts` | Advisories | see below |
| `alert_approvals` | Approval records | `alert_id`, `approver_id`, `decision`, `reason`, `decided_at` |
| `alert_deliveries` | Per channel × language | `alert_id`, `channel`, `language`, `status`, `detail`, `template_version`, `delivered_at` |

`road_segments.status_source` distinguishes `MODEL_ESTIMATED` from `OFFICER_VERIFIED` and
`OFFICIAL_CLOSURE`; the UI never presents an estimate as an official closure.

## 6. Alerts

`alerts`: `reference` unique, `zone_id`, `severity`, `status`, `headline`, `reason`,
`instructions`, `onset`, `expires`, `geometry` (GeoJSON snapshot), `threatened_assets` JSON,
`source`, `disclaimer`, `template_version`, `language`, `hazard_index`, `priority_level`,
`policy_version`, `is_scenario`, `created_at`, `approved_at`, `approved_by`,
`rejection_reason`, `cancel_reason`.

Status set: `CANDIDATE`, `APPROVED`, `REJECTED`, `DELIVERED`, `EXPIRED`, `CANCELLED`,
`ALL_CLEAR`. Only `APPROVED`, `DELIVERED` and `ALL_CLEAR` are visible on public endpoints.

`alert_policies`: `version` unique (`policy-YYYYMMDDTHHMMSS`), `name`,
`thresholds` JSON (`WATCH`/`WARNING`/`CRITICAL`), `hysteresis_points`, `min_duration_min`,
`dedupe_window_min`, `active`, `created_by`, `created_at`. Exactly one row is active; creating an
active policy retires the previous one.

## 7. Platform

| Table | Purpose |
| --- | --- |
| `audit_logs` | Append-only: `at`, `actor_email`, `actor_role`, `action`, `entity`, `entity_id`, `reason`, `payload` JSON, `request_id`, `ip` |
| `data_sources` | Registry: `id` PK, `category`, `provider`, `licence`, `attribution`, `spatial_resolution`, `temporal_resolution`, `expected_refresh_min`, `freshness_sla_min`, `fallback_source`, `state`, `last_success_at`, `last_attempt_at`, `last_error`, `enabled`, `notes`, `coverage` |
| `ingestion_runs` | `source_id`, `status`, `records`, `message`, `started_at`, `finished_at`, `duration_ms` |
| `model_versions` | `version` PK, `kind`, `name`, `features` JSON, `training_period`, `spatial_coverage`, `validation_approach`, `status`, `metrics` JSON, `card` JSON, `released_at`, `changelog` |
| `model_evaluations` | `model_version`, `method`, `status`, `metrics` JSON, `notes`, `evaluated_at` |
| `alert_policies` | above |
| `feature_flags` | `key` PK, `enabled`, `description`, `updated_by`, `updated_at` |
| `schema_migrations` | Applied migration versions |

## 8. Conventions

- Timestamps are stored in UTC (`DateTime(timezone=True)`); serialisation appends `Z`.
- Scores are floats in 0–100; `hazard_probability` is deliberately always NULL.
- JSON columns carry the provenance needed to justify a score without re-running the model.
- Deletes are avoided for operational tables: assignments are closed, alerts cancelled, users
  deactivated. Only `user_scopes` rows are replaced on scope changes.
- Foreign keys are enforced in SQLite via `PRAGMA foreign_keys=ON`.

## 9. Moving to PostgreSQL + PostGIS

1. Set `BHUSHAKTI_DATABASE_URL=postgresql+psycopg://user:pass@host/db` and install `psycopg`.
2. Run the same migration runner once (`python -c "from app.db import run_migrations; run_migrations()"`).
3. Add a PostGIS migration that converts `districts.geometry` and `spatial_units.geometry` to
   `geometry(Polygon, 4326)` and backfills from the JSON, then add GiST indexes.
4. Keep the JSON columns; the API contract does not change. Spatial queries can then move from
   haversine-in-Python to `ST_DWithin`.
