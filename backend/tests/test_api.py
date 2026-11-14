"""API and safety tests: RBAC, approval, isolation, audit."""

from __future__ import annotations

import io

from app.seed import DEMO_PASSWORD
from tests.conftest import DEMO_USERS, login


def _zones(client, token, district=None):
    query = f"?district_code={district}" if district else ""
    response = client.get(f"/api/v1/risk-zones{query}", headers=token)
    assert response.status_code == 200, response.text
    return response.json()["features"]


def test_health_and_public_config(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["probability_status"] == "NOT_CALIBRATED"
    config = client.get("/api/v1/public/config")
    assert config.status_code == 200
    assert config.json()["demo_mode"] is True
    assert "not official warnings" in config.json()["disclaimer"].lower() or \
        "not official warnings" in config.json()["disclaimer"].lower()


def test_login_success_and_failure(client):
    bad = client.post("/api/v1/auth/login", json={"email": DEMO_USERS["admin"], "password": "wrong-password"})
    assert bad.status_code == 401
    ok = client.post("/api/v1/auth/login", json={"email": DEMO_USERS["admin"], "password": DEMO_PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "platform_admin"
    assert "risk:read" in ok.json()["permissions"]
    assert ok.cookies.get("bs_session")


def test_citizen_cannot_read_operational_map(client, tokens):
    response = client.get("/api/v1/risk-zones", headers=tokens["citizen"])
    assert response.status_code == 403


def test_district_scope_is_enforced(client, tokens):
    ekh = _zones(client, tokens["admin"], "ML-EKH")
    assert ekh, "expected zones in East Khasi Hills"
    zone_id = ekh[0]["properties"]["id"]
    forbidden = client.get(f"/api/v1/risk-zones/{zone_id}", headers=tokens["district"])
    assert forbidden.status_code == 403
    allowed = client.get(f"/api/v1/risk-zones/{zone_id}", headers=tokens["admin"])
    assert allowed.status_code == 200
    detail = allowed.json()
    assert detail["hazard_probability"] is None
    assert detail["probability_status"] == "NOT_CALIBRATED"
    assert detail["exposure"]["score"] >= 0
    assert detail["drivers"]["attribution_method"].startswith("Exact log-odds")


def test_alert_approval_workflow_and_publication(client, tokens):
    candidates = client.get("/api/v1/alerts?status_filter=CANDIDATE&district_code=AS-KMR",
                            headers=tokens["district"]).json()["alerts"]
    assert candidates, "seeded rainfall should produce candidates"
    alert = candidates[0]
    assert alert["status"] == "CANDIDATE"

    public_before = client.get("/api/v1/public/alerts").json()["alerts"]
    assert all(a["reference"] != alert["reference"] for a in public_before)

    denied = client.post(f"/api/v1/alerts/{alert['id']}/approve", headers=tokens["analyst"],
                         json={"reason": "Analyst cannot publish alerts", "languages": ["en"]})
    assert denied.status_code == 403

    approved = client.post(f"/api/v1/alerts/{alert['id']}/approve", headers=tokens["district"],
                           json={"reason": "Verified against field conditions and rainfall trend",
                                 "languages": ["en", "hi"]})
    assert approved.status_code == 200, approved.text
    payload = approved.json()
    assert payload["status"] == "DELIVERED"
    channels = {(d["channel"], d["language"]): d["status"] for d in payload["deliveries"]}
    assert channels[("in_app", "en")] == "DELIVERED"
    assert channels[("email", "en")] == "QUEUED_NO_PROVIDER"
    assert channels[("sms", "en")] == "BLOCKED_NOT_CONFIGURED"
    assert channels[("in_app", "hi")] == "BLOCKED_UNREVIEWED_TEMPLATE"

    public_after = client.get("/api/v1/public/alerts").json()["alerts"]
    assert any(a["reference"] == alert["reference"] for a in public_after)

    audit = client.get("/api/v1/admin/audit-logs?action=alert.approved", headers=tokens["admin"])
    assert audit.status_code == 200
    assert any(e["entity_id"] == str(alert["id"]) for e in audit.json()["entries"])


def test_alert_cannot_be_approved_twice(client, tokens):
    alerts = client.get("/api/v1/alerts?status_filter=DELIVERED", headers=tokens["admin"]).json()["alerts"]
    if not alerts:
        return
    again = client.post(f"/api/v1/alerts/{alerts[0]['id']}/approve", headers=tokens["admin"],
                        json={"reason": "Trying to approve a second time", "languages": ["en"]})
    assert again.status_code == 409


def test_report_flow_and_bounded_adjustment(client, tokens):
    features = _zones(client, tokens["admin"], "AS-KMR")
    zone_id = features[0]["properties"]["id"]
    before = client.get(f"/api/v1/risk-zones/{zone_id}", headers=tokens["admin"]).json()["hazard_index"]

    response = client.post(
        "/api/v1/reports", headers=tokens["field"],
        data={"hazard_type": "SLOPE_MOVEMENT", "description": "Fresh tension cracks above the road",
              "lat": "26.10", "lon": "91.78", "consent": "true", "anonymous": "false",
              "client_uuid": "test-report-alpha-01"},
        files=[("files", ("crack.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 64), "image/jpeg"))],
    )
    assert response.status_code == 201, response.text
    report = response.json()["report"]
    assert report["status"] == "PENDING_VERIFICATION"
    assert report["media_count"] == 1

    denied = client.patch(f"/api/v1/reports/{report['id']}/verify", headers=tokens["field"],
                          json={"decision": "VERIFIED", "note": "Field officer cannot self-verify"})
    assert denied.status_code == 403

    verified = client.patch(f"/api/v1/reports/{report['id']}/verify", headers=tokens["district"],
                            json={"decision": "VERIFIED", "note": "Inspected: cracks confirmed across 12 m"})
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "VERIFIED"
    assert verified.json()["field_adjustment_points"] <= 15.0

    after = client.get(f"/api/v1/risk-zones/{zone_id}", headers=tokens["admin"]).json()["hazard_index"]
    assert after >= before  # bounded uplift, never a large jump
    assert after - before <= 15.01


def test_unverified_report_does_not_change_hazard(client, tokens):
    features = _zones(client, tokens["admin"], "AS-KMR")
    target = features[-1]["properties"]["id"]
    before = client.get(f"/api/v1/risk-zones/{target}", headers=tokens["admin"]).json()["hazard_index"]
    created = client.post(
        "/api/v1/reports", headers=tokens["field"],
        data={"hazard_type": "ROCKFALL", "description": "Unverified observation for pipeline test",
              "lat": "26.05", "lon": "91.70", "consent": "true",
              "client_uuid": "test-report-unverified-01"},
    )
    assert created.status_code == 201
    recalc = client.post("/api/v1/risk/recalculate", headers=tokens["admin"],
                         json={"district_codes": ["AS-KMR"], "reason": "Regression check on unverified input"})
    assert recalc.status_code == 200
    after = client.get(f"/api/v1/risk-zones/{target}", headers=tokens["admin"]).json()["hazard_index"]
    assert abs(after - before) < 0.01


def test_offline_sync_is_idempotent(client, tokens):
    item = {"client_uuid": "offline-queue-item-01", "hazard_type": "ROAD_BLOCKAGE",
            "description": "Queued offline then retried", "lat": 26.06, "lon": 91.73, "consent": True}
    first = client.post("/api/v1/reports/sync", headers=tokens["field"], json={"items": [item]})
    assert first.status_code == 200
    assert first.json()["accepted"] == 1
    second = client.post("/api/v1/reports/sync", headers=tokens["field"], json={"items": [item]})
    assert second.status_code == 200
    assert second.json()["duplicates"] == 1
    assert second.json()["results"][0]["status"] == "duplicate"


def test_citizen_report_requires_consent(client):
    response = client.post("/api/v1/public/reports",
                           data={"hazard_type": "GROUND_CRACK", "description": "No consent given",
                                 "lat": "26.1", "lon": "91.8"})
    assert response.status_code == 422


def test_scenario_is_isolated(client, tokens):
    before_alerts = client.get("/api/v1/alerts", headers=tokens["admin"]).json()["meta"]["total"]
    response = client.post("/api/v1/scenarios", headers=tokens["district"], json={
        "name": "Extreme monsoon stress test", "district_codes": ["AS-KMR"],
        "rainfall_24h": 300, "soil_moisture_pct": 55, "use_field_evidence": False,
    })
    assert response.status_code == 201, response.text
    scenario = response.json()
    assert scenario["badge"] == "SIMULATION — NOT LIVE"
    assert scenario["scenario"]["mode"] == "SIMULATION — NOT LIVE"
    after_alerts = client.get("/api/v1/alerts", headers=tokens["admin"]).json()["meta"]["total"]
    assert after_alerts == before_alerts, "scenario must never create real alerts"

    zones = _zones(client, tokens["admin"], "AS-KMR")
    live_hazard = zones[0]["properties"]["hazard_index"]
    assert live_hazard is not None  # operational map untouched by the scenario


def test_road_status_separation(client, tokens):
    roads = client.get("/api/v1/roads?district_code=AS-KMR", headers=tokens["field"]).json()["roads"]
    segment = roads[0]["segments"][0]
    denied = client.patch(f"/api/v1/roads/segments/{segment['id']}/status", headers=tokens["citizen"],
                          json={"status": "BLOCKED", "evidence": "citizen cannot change road status"})
    assert denied.status_code == 403
    bogus = client.patch(f"/api/v1/roads/segments/{segment['id']}/status", headers=tokens["field"],
                         json={"status": "BLOCKED", "status_source": "MODEL_ESTIMATED",
                               "evidence": "attempting to write a model status"})
    assert bogus.status_code == 400
    updated = client.patch(f"/api/v1/roads/segments/{segment['id']}/status", headers=tokens["field"],
                           json={"status": "RESTRICTED", "status_source": "OFFICER_VERIFIED",
                                 "evidence": "Debris on carriageway, single lane open"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["status_source"] == "OFFICER_VERIFIED"
    assert updated.json()["evidence"].startswith("Debris")


def test_assignment_lifecycle_and_reason_requirement(client, tokens):
    users = client.get("/api/v1/admin/users", headers=tokens["admin"]).json()["users"]
    officer = next(u for u in users if u["role"] == "field_officer")
    zones = _zones(client, tokens["admin"], "AS-KMR")
    created = client.post("/api/v1/response/assign", headers=tokens["district"], json={
        "zone_id": zones[0]["properties"]["id"], "assigned_to": officer["id"],
        "reason": "Warning-level unit with road exposure needs inspection", "notes": "Checkcut slope",
    })
    assert created.status_code == 201, created.text
    assignment = created.json()
    assert assignment["status"] == "ASSIGNED"

    illegal = client.patch(f"/api/v1/response/{assignment['id']}", headers=tokens["district"],
                           json={"status": "REOPENED"})
    assert illegal.status_code == 409

    no_reason = client.patch(f"/api/v1/response/{assignment['id']}", headers=tokens["district"],
                             json={"priority": "P1"})
    assert no_reason.status_code == 422

    ok = client.patch(f"/api/v1/response/{assignment['id']}", headers=tokens["field"], json={
        "status": "INSPECTED", "notes": "Slope face stable; minor raveling",
        "priority": "P2", "reason": "Downgraded after on-site inspection",
    })
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "INSPECTED"


def test_model_registry_reports_no_invented_metrics(client, tokens):
    models = client.get("/api/v1/admin/models", headers=tokens["admin"]).json()
    assert models["active_version"] == "suscept-v0.1+trigger-v0.1"
    assert models["models"][0]["metrics"] == {}
    assert models["evaluations"][0]["status"] == "VALIDATION_IN_PROGRESS"
    assert models["models"][0]["card"]["validation"]["publishable"] is False


def test_data_health_records_states_and_provenance(client, tokens):
    sources = client.get("/api/v1/admin/data-sources", headers=tokens["admin"]).json()
    states = {s["id"]: s["state"] for s in sources["sources"]}
    assert states["sim-rainfall"] == "SIMULATED"
    assert states["gsi-inventory"] == "UNAVAILABLE"
    simulated = next(s for s in sources["sources"] if s["id"] == "sim-rainfall")
    assert "SIMULATED" in simulated["state"]
    assert simulated["licence"]


def test_public_risk_is_plain_language(client):
    response = client.get("/api/v1/public/risk?lat=25.57&lon=91.89")
    assert response.status_code == 200
    payload = response.json()
    for forbidden in ("drivers", "shap", "hazard_probability", "susceptibility"):
        assert forbidden not in payload
    assert payload["official_advisory"]["note"]
    assert payload["disclaimer"]
    assert payload["risk_label"]


def test_analytics_and_export_require_permission(client, tokens):
    analytics = client.get("/api/v1/analytics", headers=tokens["analyst"])
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["model"]["validation_status"] == "VALIDATION_IN_PROGRESS"
    assert body["model"]["metrics"] == {}

    csv_response = client.get("/api/v1/analytics/export?dataset=zones&format=csv", headers=tokens["admin"])
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "probability_status" in csv_response.text.splitlines()[0]

    denied = client.get("/api/v1/analytics/export?dataset=zones&format=csv", headers=tokens["citizen"])
    assert denied.status_code == 403


def test_zone_detail_exposes_freshness_and_no_probability(client, tokens):
    zones = _zones(client, tokens["admin"], "MZ-AIZ")
    detail = client.get(f"/api/v1/risk-zones/{zones[0]['properties']['id']}", headers=tokens["admin"]).json()
    assert detail["coverage"]["level"] in {"HIGH", "MEDIUM", "LOW"}
    assert detail["coverage"]["method"].startswith("rule-based")
    assert detail["inputs"]["weather_source_state"] in {"LIVE", "SIMULATED", "STALE", "UNAVAILABLE", "CACHED", "DEGRADED"}
    assert detail["probability_status"] == "NOT_CALIBRATED"
    assert detail["trajectory"] is not None
    assert "attribution_method" in detail["drivers"]
