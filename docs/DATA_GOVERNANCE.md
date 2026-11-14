# Data governance

## 1. Principles

1. **Provenance is part of the data.** Every assessment stores the source id, source state and
   observation time of the weather it used; every source row records provider, licence,
   resolution and attribution.
2. **Simulated data is never disguised.** Demo rainfall is labelled `SIMULATED`; demo land cover,
   geology and exposure carry `SIMULATED` provenance in the registry and in the UI.
3. **No invented observations.** A source with no adapter is `UNAVAILABLE` and its ingestion
   endpoint returns 409 instead of generating values.
4. **Minimum necessary personal data.** Citizen reports are anonymous by default; identity is
   optional; GPS and media require explicit consent.
5. **Human authority over consequence.** Data can raise a candidate, only an authorised person
   can publish an advisory.

## 2. Source register

| Source | Provider | Licence / terms | Resolution | State in demo |
| --- | --- | --- | --- | --- |
| Rainfall (forecast + archive) | Open-Meteo | CC BY 4.0, attribution required | ~11 km grid, hourly | LIVE when fetched; SIMULATED profile used for assessments in demo mode |
| Soil moisture | Open-Meteo | CC BY 4.0 | ~11 km, hourly | LIVE |
| Elevation / DEM | Copernicus DEM GLO-90 via Open-Meteo | Copernicus licence, attribution | 90 m | LIVE at seed time |
| Basemap tiles | OpenStreetMap contributors | ODbL | vector/raster tiles | LIVE in the browser |
| Administrative boundaries | Approximate envelopes authored for this prototype | Internal | district bbox | SIMULATED / indicative, labelled |
| Infrastructure & roads | Demo dataset | Internal | point / line | SIMULATED |
| Landslide inventory | Demo dataset | Internal | point | SIMULATED (synthetic = 1) |
| Land cover | not ingested | — | — | UNAVAILABLE (demo factor) |
| Geology / lithology | not ingested (GSI licence needed) | — | — | UNAVAILABLE (demo factor) |
| SMS gateway | not configured | DLT registration required | — | UNAVAILABLE |
| CAP aggregator | not configured | — | — | UNAVAILABLE |

Attribution strings are exposed by `GET /api/v1/public/config` and `GET /api/v1/admin/data-sources`
and rendered in the data-health screen and the citizen footer.

## 3. Data quality states

| State | Meaning |
| --- | --- |
| `LIVE` | Real call succeeded and the observation is inside the freshness SLA |
| `CACHED` | Last good value inside a wider tolerance |
| `STALE` | Older than the SLA; hazard is still computed but coverage drops |
| `DEGRADED` | Partial failure (e.g. some windows missing) |
| `SIMULATED` | Generated demonstration values, never a real observation |
| `UNAVAILABLE` | No adapter, no credentials, or the call failed |

Freshness SLAs are stored per source (`freshness_sla_min`) and evaluated at request time, so a
source that was LIVE yesterday is shown as STALE today without any manual step.

## 4. Personal data (DPDP Act 2023 posture)

- **Consent:** GPS coordinates or media require an explicit consent flag; the API rejects the
  request otherwise with a 422 and a plain-language message. Consent is stored on the report.
- **Anonymity:** citizen submissions are anonymous by default; a name is optional. Officer
  submissions record the authenticated user as reporter.
- **Purpose limitation:** report data is used for verification and response. It is not exposed
  publicly, not sold, and not used for model training in this build.
- **Media:** stored outside the web root under `backend/storage/reports/YYYY/MM/`, hashed with
  SHA-256, type-checked by magic bytes, size-capped, EICAR-scanned. Files are served only through
  authenticated endpoints (no directory listing).
- **Retention:** no automatic deletion job exists. Recommended policy: media 24 months, report
  coordinates 36 months, audit logs 7 years under a records-retention schedule. This must be
  implemented and approved before production use — it is listed in `LIMITATIONS.md`.
- **Access:** district scoping applies to reports; a district administrator cannot read another
  district's reports. Platform and state administrators can.
- **Logs:** the audit log records actor email, role, action, reason and IP — not report content or
  passwords. Passwords are stored only as PBKDF2 hashes.

## 5. Simulated content register

| Content | Where | Label |
| --- | --- | --- |
| Monsoon rainfall profile (140–260 mm/24 h) | `sim-rainfall` source | `SIMULATED` state, demo banner |
| Land-cover factor | unit attributes | `SIMULATED` in registry/provenance |
| Geology factor | unit attributes | `SIMULATED` in registry/provenance |
| Infrastructure assets, roads, corridors | exposure | `SIMULATED`, `demo-exposure` source |
| Landslide inventory | history/analytics | `synthetic = 1`, counted separately in analytics |
| Population estimates | exposure | Approximate district figures, labelled as estimates |
| District envelopes | map | "approximate, indicative" note in API and UI |

## 6. Data sharing

- Public: district list, approved advisories, a location's plain-language risk level, source
  attribution, disclaimer.
- Never public: model internals, SHAP-style attribution, probability, unapproved candidates,
  report identities, media, audit logs, exact asset inventories.
- Exports (CSV/GeoJSON) require `analytics:export` and are scoped like the API. They contain
  scores and provenance, not personal data.

## 7. Change control

| Change | Control |
| --- | --- |
| New data source | Register row, adapter, freshness SLA, licence, attribution, tests |
| New model version | New `model_versions` row + card + validation gate + approval |
| Threshold change | New `alert_policies` row; previous version retired, not edited |
| Feature flag | `PATCH /admin/feature-flags/{key}` with audit entry |
| Schema change | New migration file; never edit an applied one |
| Deletion request | Manual today (no self-service endpoint); audit the action |

## 8. Open governance items

1. Formal data-sharing agreements with the state disaster management authorities.
2. GSI lithology licence and ESA WorldCover ingestion to remove simulated features.
3. Retention job and documented deletion procedure.
4. Native-speaker review of the four non-English templates.
5. Independent validation of the model before any public-facing use.
