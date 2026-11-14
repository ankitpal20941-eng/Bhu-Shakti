# API documentation

Base path: `/api/v1`. Interactive schema: `GET /api/docs`, OpenAPI JSON: `GET /api/openapi.json`.

## 1. Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "analyst@bhushakti.demo", "password": "BhuShakti#2026"}
```

Returns `{token, expires_at, user, permissions}` and sets an HttpOnly `bs_session` cookie
(`SameSite=Lax`, `Secure` in production, 12 h default). Clients may authenticate either with the
cookie (browser) or `Authorization: Bearer <token>` (PWA / scripts).

Other auth routes: `POST /auth/logout`, `GET /auth/me`, `GET /auth/demo-accounts` (demo mode
only). Login failures are rate limited (10/min/IP by default) and audited.

## 2. Error envelope

Every error, including validation and unhandled exceptions, looks like:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [{"location": "body.email", "message": "value is not a valid email address"}]
  },
  "request_id": "49b3feca610846ca924e4549d39549d9"
}
```

Status codes used: 400 malformed, 401 unauthenticated, 403 permission/scope, 404 unknown,
409 conflict (duplicate, illegal transition, no executable model), 422 semantic validation,
429 rate limited, 503 no current assessment.

## 3. Endpoints

### Risk

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/risk/summary` | `risk:read` | KPI totals, distribution, thresholds, per-district conditions with source state |
| GET | `/risk-zones` | `zone:read` | GeoJSON FeatureCollection; filters `district_code`, `risk_level`, `priority_level`, `search`, `limit`, `offset` |
| GET | `/risk-zones/{id}` | `zone:read` | Full detail: inputs, drivers, coverage, exposure, vulnerability, priority, field evidence, trajectory, incidents, reports, roads, history, alerts, provenance |
| GET | `/risk-zones/{id}/explanation` | `zone:read` | Drivers + narrative only |
| GET | `/risk/trajectory?zone_id=…` | `risk:read` | 6/12/24/48 h points; missing horizons are listed with the reason |
| POST | `/risk/recalculate` | `risk:recalculate` | Re-runs the pipeline; returns counts and the new distribution |

`hazard_probability` is `null` and `probability_status` is `NOT_CALIBRATED` in every risk payload.

### Weather, terrain, exposure

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/weather` | `weather:read` |
| GET | `/roads` | `roads:read` |
| PATCH | `/roads/segments/{id}/status` | `roads:write` (body: `status`, `status_source`, `evidence`) |
| GET | `/infrastructure` | `infra:read` |
| GET | `/incidents` | `incidents:read` |

### Reports

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/reports` | `reports:read` | Filter by status, district |
| POST | `/reports` | `reports:create` | `multipart/form-data`; `client_uuid` makes it idempotent |
| GET | `/reports/{id}` | `reports:read` | |
| PATCH | `/reports/{id}/verify` | `reports:verify` | `{decision: "VERIFIED"|"REJECTED", note, adjustment_points?}` |
| POST | `/reports/sync` | `reports:create` | `{items: [...]}` → per-item `accepted`/`duplicate`/`failed` |

Uploads: JPEG/PNG/WebP/MP4, magic-byte checked, 10 MB per file, 3 files per report, EICAR
rejected. GPS or media requires explicit consent.

### Alerts

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/alerts` | `alerts:read` | `status_filter` |
| GET | `/alerts/{id}` | `alerts:read` | |
| POST | `/alerts/generate` | `alerts:prepare` | Runs the policy over current assessments |
| POST | `/alerts/manual-candidate` | `alerts:prepare` | `{zone_id, reason}`; creates CANDIDATE only |
| POST | `/alerts/{id}/approve` | `alerts:approve` | `{reason (≥8 chars), languages: [...]}` |
| POST | `/alerts/{id}/reject` | `alerts:approve` | `{reason}` |
| POST | `/alerts/{id}/cancel` | `alerts:cancel` | `{reason, all_clear?: bool}` |
| GET | `/alerts/{id}/cap` | `alerts:read` | CAP-shaped JSON draft (not broadcast) |

### Response

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/response` | `response:read` | `status_filter`, `assigned_to=me`, counts, lifecycle |
| POST | `/response/assign` | `response:write` | `{zone_id, assigned_to?, reason}` |
| PATCH | `/response/{id}` | `response:write` | `{status?, priority?, notes?, reason}`; priority change requires a reason |

Allowed transitions: `DETECTED→REVIEWED|ASSIGNED`, `REVIEWED→ASSIGNED|RESOLVED`,
`ASSIGNED→INSPECTED|REVIEWED|RESOLVED`, `INSPECTED→RESOLVED`, `RESOLVED→REOPENED`,
`REOPENED→ASSIGNED|INSPECTED|RESOLVED`.

### Scenarios

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/scenarios` | `scenarios:run` | Recent runs with summary |
| POST | `/scenarios` | `scenarios:run` | `{name, district_codes?, rainfall_24h, soil_moisture_pct, use_field_evidence}` |
| GET | `/scenarios/{id}` | `scenarios:run` | Baseline vs scenario, top changes, assumptions |

### Analytics

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/analytics` | `analytics:read` | Risk by district/level/priority/coverage, rainfall series, inventory, alert and response metrics, validation state |
| GET | `/analytics/export?dataset=zones|alerts|reports&format=csv|geojson` | `analytics:export` | Streams a file |

### Admin

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/admin/data-sources` | `sources:read` |
| POST | `/admin/data-sources/{id}/ingest` | `sources:write` (only implemented adapters) |
| GET | `/admin/audit-logs` | `audit:read` (`action`, `entity`, `limit`, `offset`) |
| GET | `/admin/models` | `models:read` |
| POST | `/admin/models/{version}/activate` \| `/rollback` | `models:write` |
| GET/POST | `/admin/alert-policy` | `risk:read` / `flags:write` |
| GET | `/admin/feature-flags` | `admin:read` |
| PATCH | `/admin/feature-flags/{key}` | `flags:write` |
| GET/POST | `/admin/users` | `users:read` / `users:write` |
| PATCH | `/admin/users/{id}` | `users:write` |
| GET | `/admin/system-health` | `admin:read` |

### Stream and public

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/stream` | token (query or cookie) | SSE: `risk.updated`, `alert.created`, `alert.updated`, `report.created`, `assignment.updated`, `feed.degraded` |
| GET | `/stream/status` | `risk:read` | subscriber count |
| GET | `/public/config` | none | districts, languages, reviewed languages, features, attribution, disclaimer |
| GET | `/public/risk?lat&lon&lang` | none | plain-language local risk; nearest unit within 25 km |
| GET | `/public/alerts` | none | approved advisories only (404 when the flag is off) |
| POST | `/public/reports` | none, 5/min/IP | citizen report; consent required |
| GET | `/health` | none | DB check, version, environment |

## 4. Example: zone detail

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@bhushakti.demo","password":"BhuShakti#2026"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/risk-zones/1 | python -m json.tool
```

Response highlights:

```json
{
  "hazard_index": 62.4,
  "hazard_level": "WARNING",
  "hazard_probability": null,
  "probability_status": "NOT_CALIBRATED",
  "priority_level": "P3",
  "coverage": {"level": "MEDIUM", "points": 4, "max_points": 9, "reasons": ["..."]},
  "drivers": {"attribution_method": "exact log-odds decomposition", "top_risk_increasing": ["..."]},
  "trajectory": {"supported_horizons": [6, 12], "unavailable_horizons": [24, 48]}
}
```

## 5. Idempotency and concurrency

- Reports: unique `client_uuid`; replays return the original record with `duplicate: true`.
- Alerts: policy dedupe window per unit and severity; a second candidate cannot open while an
  approved alert for the same unit is live.
- Assignments: illegal transitions return 409, not a silent write.
- Model activation: versions without an executable implementation return 409 rather than
  pretending the switch happened.
