# BHUSHAKTI AI

Landslide early-warning and risk-intelligence platform for India's North Eastern Region
(NER). It is a working prototype: a real FastAPI + SQLAlchemy backend, a real React/TypeScript
operations console, real terrain ingestion, database-backed alerts with human approval, and
tests that enforce the safety rules.

**It is not an operational warning system.** Hazard is an uncalibrated 0–100 index, not a
probability, and no accuracy metric is published anywhere in this build.

```
SENSE → PREDICT → EXPLAIN → PRIORITIZE → ACT
```

Hazard answers *"how bad could the ground failure be?"*. Priority answers *"what should the
district do first?"*. They are computed and stored separately, because a hazardous slope with
nothing exposed is not P1.

---

## 1. What is in the repository

| Path | Contents |
| --- | --- |
| `backend/app` | FastAPI application: routers, engine, services, models, seed |
| `backend/migrations` | Versioned SQL migrations applied by the in-app migration runner |
| `backend/tests` | 41 pytest tests (engine safety, validation gate, API contracts) |
| `backend/data` | Development SQLite database (generated, not source) |
| `backend/storage` | Uploaded report media (generated, not source) |
| `frontend/src` | React 18 + TypeScript + Vite application |
| `docs` | Architecture, schema, API, ML, governance, security, deployment, limitations, ADRs |

## 2. Quick start (Windows / macOS / Linux)

Prerequisites: Python 3.11+ (verified on 3.14), Node 18+.

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. API docs: <http://127.0.0.1:8000/api/docs>.

If port 8000 is already taken (it can be, if another service is running), start the API on 8001
and point the dev proxy at it:

```bash
cd backend  && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd frontend && VITE_PROXY_TARGET=http://127.0.0.1:8001 npm run dev
```

### Database

The first start creates `backend/data/bhushakti.db` and applies `backend/migrations`. To rebuild
the demo dataset from scratch (it re-samples the live DEM and re-runs the pipeline):

```bash
cd backend
rm -rf data
python -c "from app.db import run_migrations; run_migrations()"
python -c "from app.db import SessionLocal; from app.seed import seed_database; s=SessionLocal(); seed_database(s); s.close()"
```

Seeding needs outbound HTTPS to `api.open-meteo.com`. If the DEM call fails, terrain falls back
to an explicitly labelled synthetic profile and the data-health screen shows it as degraded.

### Demo accounts (`BHUSHAKTI_ENV=demo`)

Password for every seeded account: `BhuShakti#2026`

| Email | Role | Scope |
| --- | --- | --- |
| `admin@bhushakti.demo` | Platform Administrator | statewide |
| `state.assam@bhushakti.demo` | State Administrator | Assam |
| `dc.kamrup@bhushakti.demo` | District Administrator | Kamrup Metropolitan |
| `analyst@bhushakti.demo` | Authority Analyst | all three districts |
| `field.officer@bhushakti.demo` | Field Officer | Kamrup Metropolitan |
| `citizen@bhushakti.demo` | Citizen | public pages only |
| `researcher@bhushakti.demo` | Researcher | read-only analytics |

These accounts exist only in demo mode. Setting `BHUSHAKTI_ENV=production` disables demo mode,
and therefore the demo-accounts endpoint and the seeded accounts path, at configuration level.

## 3. The five-stage pipeline

1. **SENSE** — weather (Open-Meteo, live or simulated), soil moisture (Open-Meteo, live),
   terrain (Copernicus DEM GLO-90 sampled through the Open-Meteo elevation API, live), plus
   officer-verified field reports.
2. **PREDICT** — susceptibility `S` from a deterministic logistic form with expert-set weights,
   a rainfall trigger `T` from a Caine-style intensity–duration envelope, combined
   multiplicatively: `hazard = 100 · (S/100) · (0.20 + 0.80·T/100)`. Missing weather halves the
   trigger and reduces coverage.
3. **EXPLAIN** — exact log-odds decomposition of the static terms (not SHAP), rainfall ratios,
   soil-moisture factor, field-evidence points and the coverage checklist.
4. **PRIORITIZE** — `priority = 0.60·hazard + 0.25·exposure + 0.15·vulnerability`, banded
   P1 ≥ 75, P2 ≥ 55, P3 ≥ 35, P4 below.
5. **ACT** — candidates → human approval → channel deliveries, response assignments, road
   status, public advisories.

## 4. Feature status

| Area | Status |
| --- | --- |
| Hazard engine, drivers, trajectory, coverage | IMPLEMENTED AND TESTED |
| Live DEM ingestion + terrain features | IMPLEMENTED AND TESTED (live calls during seed) |
| Live rainfall / soil adapters | IMPLEMENTED, VERIFIED BY LIVE CALL; demo assessments use SIMULATED rainfall |
| Alert candidates, approval, rejection, cancel, all-clear, deliveries, CAP draft | IMPLEMENTED AND TESTED |
| Response lifecycle with required reasons | IMPLEMENTED AND TESTED |
| Field reports, media validation, verification, bounded adjustment | IMPLEMENTED AND TESTED |
| Offline queue + idempotent sync | IMPLEMENTED; single-device flow exercised manually, not automated |
| Scenario lab isolation from operational data | IMPLEMENTED AND TESTED |
| Citizen portal (public risk, advisories, reporting) | IMPLEMENTED; API smoke-tested, UI not clicked through |
| Analytics + CSV/GeoJSON export | IMPLEMENTED AND TESTED |
| Model registry / validation gate | IMPLEMENTED AND TESTED (gate refuses to publish metrics) |
| SMS / email delivery | NOT AVAILABLE — no provider or DLT registration; attempts recorded as BLOCKED |
| Image AI (crack detection) | PLANNED — flag exists, disabled, no model |
| PostGIS geometry, vector tiles, time slider | PLANNED — JSON geometry + bbox filters today |
| Celery / Redis background workers | NOT AVAILABLE — in-process scheduler instead |

Full detail, including unverified items: [docs/LIMITATIONS.md](docs/LIMITATIONS.md) and the
delivery report in section 9.

## 5. Safety invariants enforced in code

- `hazard_probability` is always `null`; `probability_status` is always `NOT_CALIBRATED`.
- Weather state is attached to every assessment; simulated values are never labelled LIVE.
- Alerts are born `CANDIDATE` and require a separate human approval with a reason; the approver
  and timestamp are stored and audited. Scenarios can never create alerts.
- Reports enter `PENDING_VERIFICATION`; only officer verification can adjust hazard, capped at
  +15 points with a 7-day half-life.
- Validation refuses to publish metrics for an untrained model, synthetic inventory, unsuitable
  method or too-small sample.
- District scoping is applied server-side to every list and mutation, not in the browser.

## 6. Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, request flow, decisions
- [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) — every table and the important columns
- [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) — endpoints, auth, error envelope
- [ML_METHODOLOGY.md](docs/ML_METHODOLOGY.md) — formulas, features, why no probability
- [MODEL_CARD.md](docs/MODEL_CARD.md) — intended use, limitations, validation state
- [DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) — sources, licences, consent, retention
- [SECURITY.md](docs/SECURITY.md) — authN/authZ, scoping, uploads, rate limits
- [OFFLINE_SYNC.md](docs/OFFLINE_SYNC.md) — queue, idempotency, conflict rules
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — environment variables, Postgres, reverse proxy
- [TESTING.md](docs/TESTING.md) — what the 41 tests assert and how to run them
- [LIMITATIONS.md](docs/LIMITATIONS.md) — what this build does not do
- [docs/adr](docs/adr) — architecture decision records

## 7. Tests

```bash
cd backend && python -m pytest tests -q        # 41 passed
cd frontend && npm run build                   # tsc -b + vite build
```

See [docs/TESTING.md](docs/TESTING.md) for what each suite covers.

## 8. Configuration

All settings are environment variables with safe development defaults; see
[DEPLOYMENT.md](docs/DEPLOYMENT.md#environment-variables). `BHUSHAKTI_SECRET_KEY` must be set in
any non-development environment — the app generates a per-install development secret otherwise.

## 9. Delivery report

| Feature | Status | Evidence |
| --- | --- | --- |
| Backend API (13 routers) | IMPLEMENTED AND TESTED | 41 pytest tests; live smoke of all routers |
| Frontend (11 screens) | IMPLEMENTED, BUILD VERIFIED | `npm run build` passes; app served at `/`; screens not clicked through end-to-end |
| Hazard / priority separation | IMPLEMENTED AND TESTED | `test_engine.py` |
| Alert human-approval gate | IMPLEMENTED AND TESTED | `test_api.py` approval + RBAC tests |
| Validation gate (no fake metrics) | IMPLEMENTED AND TESTED | `test_validation.py` |
| Live terrain, live weather/soil adapters | IMPLEMENTED; live calls succeeded | data-health registry, ingestion runs |
| Demo rainfall | SIMULATED (labelled) | banner + `SIMULATED` state on every affected assessment |
| Multilingual templates | PARTIAL — English reviewed, four drafts blocked from delivery | `alerts.py` |
| SMS / email / CAP broadcast | NOT AVAILABLE | deliveries recorded `BLOCKED`, no provider |
| Auth / RBAC / audit | IMPLEMENTED AND TESTED | `test_api.py`, audit endpoint |
| Offline field sync | IMPLEMENTED, PARTIALLY VERIFIED | API idempotency tested; device flow manual |
| PostGIS, Celery, MLflow, GDAL, image AI | NOT IMPLEMENTED | listed in LIMITATIONS |
