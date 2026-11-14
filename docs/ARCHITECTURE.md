# Architecture

## 1. Shape of the system

```
┌──────────────────────────── Browser (React 18 + TS) ────────────────────────────┐
│ Command Center · Risk Map · Zone drawer · Response · Alerts · Field PWA ·        │
│ Analytics · Data Health · Models · Scenarios · Admin · Citizen portal            │
│ TanStack Query (server state) · Zustand (session/UI) · MapLibre · Recharts        │
└───────────────▲───────────────────────────────────────────────┬────────────────┘
                │ JSON/SSE (cookie or Bearer)                    │ multipart uploads
┌───────────────┴───────────────────────────────────────────────▼────────────────┐
│ FastAPI (backend/app)                                                           │
│  middleware: request-id, security headers, CORS, error envelope                 │
│  routers: auth risk weather roads infrastructure reports alerts response        │
│           scenarios analytics admin stream public health                        │
│  services: risk · alerts · reports · ingestion · serializers · audit · events   │
│  engine:   params · hazard · exposure · explain · trajectory · validation       │
│  data:     SQLAlchemy 2 ORM + migration runner (SQLite dev, PostgreSQL/PostGIS) │
└───────────────▲───────────────────────────────────────────────┬────────────────┘
                │ HTTPS                                          │ filesystem
      Open-Meteo forecast / archive / elevation            backend/storage/reports
      (rainfall, soil moisture, Copernicus DEM GLO-90)
```

The backend owns every safety decision. The frontend never computes hazard, priority, coverage
or a probability; it renders what the API returns and disables actions the session's permission
list does not include (the server re-checks anyway).

## 2. Request lifecycle

1. `RequestContextMiddleware` assigns a request id, adds security headers and normalises
   unhandled exceptions into `{"error": {...}, "request_id": "..."}`.
2. `deps.current_user` resolves the session from the `bs_session` cookie or an
   `Authorization: Bearer` header, verifies the HMAC signature and expiry, loads the user and
   district scopes from the database (a disabled user is rejected even with a valid token).
3. `deps.require("permission")` checks the role matrix in `domain.py`.
4. Scope helpers restrict queries by `district_code` for non-statewide roles.
5. Mutating routes call `audit.record(...)` with actor, reason, before/after payload, request id
   and IP, then commit once.
6. Lists that feed live screens are invalidated over SSE (`/api/v1/stream`) after a write; the
   UI also falls back to 60-second polling when the stream is down.

## 3. Ingestion

| Source id | Adapter | Mode in this build |
| --- | --- | --- |
| `open-meteo-precip` | `OpenMeteoWeatherAdapter` (forecast + archive) | LIVE when fetched |
| `open-meteo-soil` | Open-Meteo soil moisture | LIVE when fetched |
| `open-meteo-dem` | `OpenMeteoElevationAdapter` (Copernicus GLO-90 via Open-Meteo) | LIVE, sampled at seed time |
| `sim-rainfall` | `SimulatedWeatherAdapter` (monsoon profile, 140–260 mm/24 h) | SIMULATED |
| `demo-exposure` | Seeded assets/corridors | SIMULATED |
| GSI lithology, ESA WorldCover, SMS gateway, CAP aggregator | none | UNAVAILABLE |

Each adapter writes an `ingestion_runs` row with status, record count, duration and error text.
`services/risk.effective_weather_state` derives LIVE / CACHED / STALE / DEGRADED / SIMULATED /
UNAVAILABLE from the source row plus observation age against the source's freshness SLA.
The registry is readable at `GET /api/v1/admin/data-sources`.

Terrain is sampled once at seed time (115 units × 5 DEM samples per unit, ±0.0025°) because the
elevation API is the expensive call; slope, aspect, ruggedness, curvature and a TWI proxy are
computed from that grid. This is a **90 m DEM**, so slope is a planning-unit indicator, not a
slope-stability survey.

## 4. Risk computation

`services/risk.compute_assessment` is the only place hazard is produced:

```
static_index  S = 100 / (1 + exp(-(b0 + Σ wᵢ·(xᵢ-μᵢ)/σᵢ)))
trigger_index T = 100 · clip(Σ ratios·weights / scale, 0, 1) · soil_factor · season_factor
hazard        H = 100 · (S/100) · (TRIGGER_FLOOR + (1-TRIGGER_FLOOR)·T/100)
priority      P = 0.60·H + 0.25·exposure + 0.15·vulnerability
```

If no usable weather exists: `T := 50`, `H ×= 0.5`, coverage drops, the assessment is stored
with `weather_source_state = UNAVAILABLE` and the UI shows "reduced coverage".

`recalculate` writes a new `risk_assessments` row per unit (never updates history in place),
attaches field evidence points, computes exposure/vulnerability/priority, fires `risk.updated`
and opens alert candidates for policy-qualifying units.

## 5. Alerts

```
approaching threshold ──► AlertPolicy (hysteresis, min duration, dedupe)
                              │
                              ▼
                     Alert(status=CANDIDATE)  ── human approval ──► APPROVED ──► deliveries
                              │                                              │
                        reject/cancel                                    cancel / all-clear
```

- The policy engine writes candidates only; there is no auto-publish path in the codebase.
- Approval requires `alerts:approve`, a reason of at least 8 characters and a language list. The
  approver id and time are stored in `alert_approvals` and mirrored into `audit_logs`.
- Only English is reviewed. Requests for `hi/as/bn/ne` produce a delivery row with status
  `BLOCKED` and the reason "translation not reviewed"; they are not silently sent.
- SMS requires a DLT-registered sender and is not configured: delivery rows are `BLOCKED`.
  Email has no provider either. CAP is a downloadable/GET JSON draft, not a broadcast.
- Public endpoints only expose `APPROVED`, `DELIVERED` and `ALL_CLEAR`.

## 6. Field reports

`reports.create_report` is idempotent on `client_uuid` (replay returns the existing row and
`duplicate: true`). Media is validated by declared type **and** magic bytes, size-capped, scanned
for the EICAR test string, hashed (SHA-256) and stored outside the web root. Reports are created
`PENDING_VERIFICATION`; `verify` (officer only, reason required) may apply a bounded evidence
adjustment that feeds the *next* assessment — never the historical one.

## 7. Scenarios

`POST /api/v1/scenarios` runs the same engine with supplied rainfall/soil values and optional
district scoping, writes `scenario_runs` and `risk_assessments` rows with `is_scenario = 1`, and
returns a comparison. Every operational query filters `is_scenario = false`; scenario rows can
never be approved, delivered or shown publicly. This is enforced by a test.

## 8. Frontend structure

```
src/
  App.tsx                 routes; /citizen is public, everything else behind Protected
  components/AppShell.tsx navigation, live indicator, demo banner, theme, low-bandwidth
  components/MapView.tsx  MapLibre: zone polygons, roads, assets, incidents, reports
  components/ZoneDrawer    evidence, drivers, exposure, trajectory, reports, alerts, history
  components/ui.tsx       design system: cards, badges, tables, drawer, modal, tabs, toasts
  hooks/useLiveUpdates    SSE bridge + polling fallback
  lib/api.ts              fetch wrapper, error envelope, download helper
  lib/offline.ts          IndexedDB queue for field reports
  lib/i18n.ts             citizen strings (5 languages; only English reviewed)
  store/session.ts        persisted token/user/permissions (Zustand)
  store/ui.ts             theme, layers, filters, live status
  pages/*.tsx             one file per screen
```

Design language: forest green + slate neutrals, tabular numerals for scores, risk colours only
on risk badges and map fills, visible focus rings, 44 px touch targets in field views, and a
print stylesheet that hides navigation.

## 9. Decisions

See [adr](adr). The load-bearing ones:

1. No calibrated probability — expose an index and say so everywhere.
2. Multiplicative hazard combination instead of noisy-OR (which saturated).
3. Human approval in the database, not just in the UI.
4. Exact log-odds attribution instead of fabricated SHAP values.
5. Explicit coverage points instead of a confidence percentage.
6. In-process scheduler instead of Celery/Redis for a single-node prototype.
