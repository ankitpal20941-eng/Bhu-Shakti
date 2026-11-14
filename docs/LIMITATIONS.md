# Limitations

Everything below is true of this build. Nothing here is a roadmap promise.

## 1. Model and science

| Limitation | Consequence |
| --- | --- |
| Weights are expert-set, not fitted | Ordering is plausible, not empirically learned |
| No calibration | Scores are not probabilities; no "x% chance" anywhere |
| No verified inventory (demo inventory is synthetic) | No skill metric can be computed |
| Land cover and geology are simulated factors | Two of nine static features are demo data |
| DEM is 90 m, sampled at ~2.2 km spacing | Local slope and cut-slope instability are smoothed away |
| TWI is a slope-based proxy | Contributing area and flow accumulation are not modelled |
| Global intensity–duration envelope × 1.35 | Not calibrated for NER rainfall regimes |
| Rainfall is a district-centre grid point | Convective cells are far smaller than a district |
| Soil moisture is a surface proxy | Deep pore pressure / antecedent groundwater not modelled |
| Trajectory uses forecast rainfall only | No hydrological routing or geotechnical modelling |
| Exposure buffer is 2.5 km around the centroid | Large or elongated units can be mis-summarised |
| Population figures are approximate | Exposure population is an estimate, labelled as such |

## 2. Data and integrations

- No GSI lithology, no ESA WorldCover, no soil survey, no InSAR, no seismic or tilt sensors.
- No SMS gateway (DLT registration required) and no email provider: delivery attempts are stored
  as `BLOCKED`, never as sent.
- No CAP broadcast: `/alerts/{id}/cap` returns a draft payload only.
- No IMD feed, no state emergency-operations-centre integration, no Bhuvan/WMS layers.
- Automatic ingestion is an in-process scheduler; there is no Celery/Redis queue, retry broker or
  dead-letter store.
- No image AI (crack segmentation) — the flag exists and is off; there is no model.
- No vector tiles, no PostGIS-native geometry, no time slider on the map; geometry is GeoJSON
  served per request with bbox/attribute filters.

## 3. Application

- SMS/email channels are placeholders: the API records `BLOCKED` with a reason, which is honest
  but means no real multi-channel dissemination exists.
- Four non-English templates (Hindi, Assamese, Bengali, Nepali) are drafts and are blocked from
  delivery until reviewed by native speakers.
- The offline queue stores text and GPS only; a photo captured offline is not persisted for later
  upload.
- The service worker caches the application shell and, network-first, a few read-only GETs
  (risk summary, zones, public endpoints). Cached snapshots can be minutes old and are not marked
  with a "cached" badge in the UI; writes always require connectivity.
- No password reset, MFA, SSO, account lockout beyond rate limiting, or self-service profile
  management.
- No retention/deletion job for report media or audit logs.
- No background export queue: CSV/GeoJSON exports are generated synchronously.
- No notification inbox or email digest for assignments.

## 4. Operations

- Single-node design: in-process rate limiting and scheduling assume one worker.
- Forward-only migrations; no down-migrations.
- No container image, Kubernetes manifests, Terraform or CI pipeline in this repository.
- No structured log shipping, metrics endpoint (Prometheus), or alerting on pipeline failure.
  The data-health screen is the operational view.
- No load or soak testing; no capacity figures are claimed.
- Backups are manual and documented, not automated.

## 5. Verification honestly stated

- Backend: 41 automated tests pass (engine, validation gate, API contracts).
- Frontend: TypeScript + Vite production build passes; the app served and the preview was
  registered.
- API: every router plus public endpoints were smoke-tested through the dev proxy with real HTTP
  calls.
- **Not verified:** browser interaction flows (clicking through map, drawers, approve buttons),
  visual layout at multiple sizes, accessibility, the offline queue in a real browser, and any
  live-provider failure path. Those need a person at the browser or an automated UI suite.
- **Not verified in this environment:** the 8000 port was occupied by an unrelated service, so the
  API ran on 8001 with `VITE_PROXY_TARGET`. Nothing about that changes the application, but the
  deployment section documents the override.

## 6. Legal and institutional

- District envelopes are approximate and are **not** authoritative administrative boundaries.
- Road corridors and assets are indicative demo data, not a state asset register.
- No data-sharing agreement with SDMAs, IMD or GSI is in place.
- The platform is decision support. It cannot issue, and does not issue, official warnings.
