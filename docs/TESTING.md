# Testing

## 1. How to run

```bash
cd backend
python -m pytest tests -q            # 41 tests
python -m pytest tests -v            # per-test names
python -m pytest tests/test_engine.py -q

cd frontend
npm run build                        # tsc -b + vite build (type + bundle check)
npm run typecheck                    # tsc --noEmit only
```

Last recorded run: **41 passed, 3 warnings** (StarletteTestClient deprecation notices only).
Frontend: production build succeeded (2,267 modules; single bundle ~1.74 MB / 480 kB gzip).

## 2. Test layout

| File | Focus |
| --- | --- |
| `tests/conftest.py` | Isolated SQLite database per session, app factory, authenticated clients for several roles |
| `tests/test_engine.py` | Engine invariants: hazard behaviour, trigger, coverage, priority, evidence, trajectory, decomposition |
| `tests/test_validation.py` | Validation gate refuses to publish metrics under unsafe conditions |
| `tests/test_api.py` | Auth, RBAC, scoping, alert approval, reports, assignments, scenarios, models |

## 3. What the engine tests assert

- Hazard is never reported as a probability: `hazard_probability is None` and
  `probability_status == "NOT_CALIBRATED"`.
- Hazard increases monotonically with rainfall intensity, all else equal.
- Heavy rain on a flat, low-susceptibility unit stays below the warning band (no saturation).
- Missing weather halves the trigger contribution and drops coverage.
- Coverage is the rule-based checklist, and its points never exceed the maximum.
- Land-cover and geology factors move susceptibility in the documented direction.
- Field evidence is capped at +15 points and decays with a 7-day half-life; unverified reports
  contribute nothing.
- Priority is independent of the hazard band (high hazard with zero exposure can be P3/P4).
- The static attribution is exact: the sum of term contributions equals the log-odds
  (tolerance 1e-5), and every term is bounded.
- Trajectory returns only supported horizons and lists missing ones with a reason.

## 4. What the API tests assert

- Login succeeds for seeded roles and returns a permission set; bad passwords return 401.
- Protected routes return 401 without a session and 403 for a role without the permission.
- District scoping: a district administrator cannot read another district's unit or reports.
- Alert candidate → approve requires a reason; approval records approver and timestamp; the
  candidate is not visible on public endpoints before approval.
- Rejection and cancellation require a reason and are audited.
- Scenario runs are isolated: `is_scenario = true` assessments never appear in operational lists
  and cannot create alerts.
- Citizen report without consent is rejected (422); report replay with the same `client_uuid` is
  idempotent and returns `duplicate: true`; verification requires a note and is one-way.
- Assignment lifecycle rejects illegal transitions and requires a reason for priority changes.
- Model activation of an unimplemented version returns 409.
- Data-source ingestion for an adapter-less source returns 409 (nothing is fabricated).
- The validation gate returns blockers instead of metrics for the prototype.

## 5. Manual checks performed for this delivery

- Seeded the demo database: 116 units across three districts, live DEM samples, live weather and
  soil; distribution 65 SAFE / 39 WATCH / 12 WARNING / 0 CRITICAL, 12 candidates, priorities
  95 P4 / 20 P3 / 1 P2.
- Started the API and the dev server; smoke-tested every router through the vite proxy
  (risk, zones, alerts, response, scenarios, analytics, admin, roads, reports, infrastructure,
  weather, incidents, stream status), plus login as three roles, the CSV export (29 KB) and the
  public risk endpoint in English and Hindi.
- Confirmed the citizen endpoint returns `language_reviewed: false` for Hindi.

## 6. Not covered

- No browser end-to-end tests (Playwright/Cypress), no accessibility audit, no load test.
- No automated test for the IndexedDB offline queue; only the server-side sync contract is
  tested.
- No test of live provider failure paths against the real network (adapters are exercised in
  seed/ingestion, not mocked for every error).
- No migration rollback test; migrations are forward-only.
- No frontend unit tests; correctness of screens rests on the type checker and shared API types.
- No security scanning (SAST/DAST) or dependency audit in CI.

## 7. Suggested next tests

1. Playwright: sign-in → map → zone drawer → approve alert → response update.
2. Offline queue: enqueue with network disabled, restore, assert `synced` and server id.
3. Adapter contract tests with recorded HTTP fixtures and a failing-endpoint case.
4. Property-based tests for monotonicity across random feature vectors.
5. Postgres/PostGIS integration run in CI once the production schema lands.
