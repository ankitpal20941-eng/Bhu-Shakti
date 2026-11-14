"""Comprehensive multi-section seed script for BHUSHAKTI AI.

Populates realistic, geotechnical domain-accurate demonstration records for:
1. Alerts across ALL lifecycle filter states (CANDIDATE, APPROVED, DELIVERED, REJECTED, EXPIRED, ALL_CLEAR, CANCELLED)
2. Response Assignments across ALL workflow states (DETECTED, REVIEWED, ASSIGNED, INSPECTED, RESOLVED, REOPENED)
3. Notification Logs across ALL statuses (DELIVERED, PROCESSING, PENDING, FAILED)
4. Satellite Change Detections across ALL verification states (CANDIDATE_SCAR, VERIFIED_SCAR, FALSE_POSITIVE, UNDER_REVIEW)
5. Citizen & Field Reports (PENDING_VERIFICATION, VERIFIED, REJECTED)
6. Early Warning Timelines (multi-milestone lifecycle progressions)
7. Landslide Runout Envelopes (debris paths, fahrb\u00f6schung runouts, threatened settlements & roads)
8. Historical Disaster Event Records (Assam 2022, Meghalaya 2023, Mizoram 2024)
9. IoT Geotechnical Sensors & Real-time Readings
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .domain import ALERT_DISCLAIMER
from .models import (
    Alert,
    AlertDelivery,
    EarlyWarningTimelineEvent,
    HistoricalEventRecord,
    LandslideRunoutZone,
    NotificationLog,
    Report,
    ResponseAssignment,
    SatelliteChangeDetection,
    Sensor,
    SensorReading,
    SpatialUnit,
    User,
)

log = logging.getLogger("bhushakti.seed_all")


def seed_all_sections(db: Session | None = None) -> dict[str, int]:
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        now = datetime.now(timezone.utc)
        zones = db.execute(select(SpatialUnit)).scalars().all()
        if not zones:
            log.warning("No zones exist in the database. Run initial seed first.")
            return {}

        users = db.execute(select(User)).scalars().all()
        admin_user = next((u for u in users if u.role_code in ("platform_admin", "state_admin")), users[0])
        field_user = next((u for u in users if u.role_code == "field_officer"), users[0])
        analyst_user = next((u for u in users if u.role_code == "analyst"), users[0])

        zones_by_district: dict[str, list[SpatialUnit]] = {
            "AS-KMR": [z for z in zones if z.district_code == "AS-KMR"],
            "ML-EKH": [z for z in zones if z.district_code == "ML-EKH"],
            "MZ-AIZ": [z for z in zones if z.district_code == "MZ-AIZ"],
        }

        counts: dict[str, int] = {}

        # =====================================================================
        # 1. ALERTS (Seed all filter statuses)
        # =====================================================================
        # Current existing references
        existing_refs = set(db.execute(select(Alert.reference)).scalars().all())

        alert_specs = [
            # APPROVED ALERTS
            {
                "ref": "ALT-2026-APP01",
                "status": "APPROVED",
                "severity": "CRITICAL",
                "district": "AS-KMR",
                "zone_idx": 1,
                "headline": "CRITICAL Landslide Warning — Narakasur Hill Escarpment Corridor",
                "reason": "Intense 72-hour antecedent rainfall (182 mm) exceeded local weathered gneiss threshold. Active sub-surface pore pressure surge detected.",
                "instructions": "Immediate evacuation advisory for foot-slope dwellings. Divert heavy transit away from Narakasur bypass road. SDRF cadre stationed at GMCH staging area.",
                "hazard_index": 86.4,
                "priority": "P1",
                "onset_hours": -1,
                "expires_hours": 36,
                "approved": True,
            },
            {
                "ref": "ALT-2026-APP02",
                "status": "APPROVED",
                "severity": "WARNING",
                "district": "ML-EKH",
                "zone_idx": 2,
                "headline": "WARNING — Sohra-Shella Escarpment Sector C",
                "reason": "Monsoon downpour reached 215 mm/24h. Karst fissure drainage saturation creating localized toe erosion.",
                "instructions": "Caution advised along SH-5. Heavy commercial haulage prohibited until ground engineering inspection completes.",
                "hazard_index": 72.0,
                "priority": "P2",
                "onset_hours": -2,
                "expires_hours": 24,
                "approved": True,
            },
            # DELIVERED ALERTS
            {
                "ref": "ALT-2026-DEL01",
                "status": "DELIVERED",
                "severity": "CRITICAL",
                "district": "MZ-AIZ",
                "zone_idx": 1,
                "headline": "CRITICAL Slope Failure Warning — Ramhlun North Dip-Slope Belt",
                "reason": "Cyclone Remal remnant depression triggered 168 mm rainfall over saturated Surma shale bedding plane.",
                "instructions": "Activate community shelter protocol at Hawla Indoor Stadium. NH-54 arterial clearance teams on standby.",
                "hazard_index": 89.2,
                "priority": "P1",
                "onset_hours": -6,
                "expires_hours": 48,
                "approved": True,
                "delivered": True,
            },
            {
                "ref": "ALT-2026-DEL02",
                "status": "DELIVERED",
                "severity": "WARNING",
                "district": "AS-KMR",
                "zone_idx": 4,
                "headline": "WARNING — Khanapara Hill Edge Settlement Corridor",
                "reason": "Continuous antecedent rainfall (145 mm) softening cut-slope embankments along the Meghalaya border fringe.",
                "instructions": "Residents in valley bottoms to maintain watch. Emergency services pre-positioned at Dispur Command Station.",
                "hazard_index": 68.5,
                "priority": "P2",
                "onset_hours": -12,
                "expires_hours": 18,
                "approved": True,
                "delivered": True,
            },
            # REJECTED ALERTS
            {
                "ref": "ALT-2026-REJ01",
                "status": "REJECTED",
                "severity": "WARNING",
                "district": "ML-EKH",
                "zone_idx": 5,
                "headline": "Candidate WARNING — Upper Shillong Peak Ridge Unit 14",
                "reason": "Automated trigger calculated warning based on gridded radar rain spike (74 mm/h).",
                "instructions": "Proposed vehicular diversion along Elephant Falls bypass.",
                "hazard_index": 63.0,
                "priority": "P2",
                "onset_hours": -4,
                "expires_hours": 20,
                "rejected": True,
                "rejection_reason": "On-ground geotechnical inspection by SDRF Unit ML-SDRF-01 confirmed radar artifact. Rain gauge at site recorded only 12 mm; soil drainage intact. Alert rejected.",
            },
            {
                "ref": "ALT-2026-REJ02",
                "status": "REJECTED",
                "severity": "WATCH",
                "district": "AS-KMR",
                "zone_idx": 6,
                "headline": "Candidate WATCH — Chandrapur Brahmaputra Bluffs",
                "reason": "Riverbank erosion telemetry flagged localized slope displacement.",
                "instructions": "Inland settlement advisory.",
                "hazard_index": 38.0,
                "priority": "P3",
                "onset_hours": -8,
                "expires_hours": 16,
                "rejected": True,
                "rejection_reason": "Dual-authorization review: Brahmaputra Board confirmed scouring is aquatic bank erosion, not geotechnical hillside failure. Diverted to Flood Control Cell.",
            },
            # EXPIRED ALERTS
            {
                "ref": "ALT-2026-EXP01",
                "status": "EXPIRED",
                "severity": "WARNING",
                "district": "MZ-AIZ",
                "zone_idx": 3,
                "headline": "Expired WARNING — Tuirial Valley Road Segment km 14",
                "reason": "Historical monsoon pulse (112 mm) triggered temporary warning envelope.",
                "instructions": "Transit caution between Aizawl and Airport highway.",
                "hazard_index": 66.0,
                "priority": "P2",
                "onset_hours": -72,
                "expires_hours": -24,  # expired in past
                "approved": True,
            },
            {
                "ref": "ALT-2026-EXP02",
                "status": "EXPIRED",
                "severity": "WATCH",
                "district": "ML-EKH",
                "zone_idx": 7,
                "headline": "Expired WATCH — Pynursla Ridge Cut-Slope",
                "reason": "Pre-monsoon shower accumulation triggered standard watch threshold.",
                "instructions": "Standard highway monitoring.",
                "hazard_index": 42.0,
                "priority": "P3",
                "onset_hours": -96,
                "expires_hours": -48,
                "approved": True,
            },
            # ALL_CLEAR ALERTS
            {
                "ref": "ALT-2026-CLR01",
                "status": "ALL_CLEAR",
                "severity": "WATCH",
                "district": "AS-KMR",
                "zone_idx": 2,
                "headline": "ALL-CLEAR Declared — Nilachal Hill Kamakhya Access Corridor",
                "reason": "Previous warning period expired. Subsequent 48h dry spell with piezometric levels returning below safety thresholds.",
                "instructions": "All normal vehicular access resumed. Retaining wall construction certified stable by PWD engineering team.",
                "hazard_index": 22.0,
                "priority": "P3",
                "onset_hours": -18,
                "expires_hours": 12,
                "all_clear": True,
                "cancel_reason": "Engineering inspection verified no ongoing deformation. 48 hours zero rainfall.",
            },
            {
                "ref": "ALT-2026-CLR02",
                "status": "ALL_CLEAR",
                "severity": "WATCH",
                "district": "MZ-AIZ",
                "zone_idx": 4,
                "headline": "ALL-CLEAR Declared — Bawngkawn Ridge Sector 3",
                "reason": "Stabilization dewatering completed. Tensile crack monitors show zero movement over 72 hours.",
                "instructions": "Residents safe to re-occupy surveyed hillside structures.",
                "hazard_index": 24.5,
                "priority": "P3",
                "onset_hours": -30,
                "expires_hours": 6,
                "all_clear": True,
                "cancel_reason": "Geotechnical clearance certificate issued by Disaster Management Authority.",
            },
            # CANCELLED ALERTS
            {
                "ref": "ALT-2026-CAN01",
                "status": "CANCELLED",
                "severity": "CRITICAL",
                "district": "ML-EKH",
                "zone_idx": 8,
                "headline": "Cancelled CRITICAL Advisory — Mawkdok Dympep Bridge Abutment",
                "reason": "Heavy runoff triggered initial sensor acceleration warning.",
                "instructions": "Precautionary traffic halt on Sohra Highway.",
                "hazard_index": 82.0,
                "priority": "P1",
                "onset_hours": -5,
                "expires_hours": 19,
                "cancelled": True,
                "cancel_reason": "Emergency bridge abutment inspection confirmed bedrock intact. Heavy machinery vibration caused false seismic trigger. Withdrawn by District Collector.",
            },
        ]

        alerts_added = 0
        deliveries_added = 0

        for spec in alert_specs:
            if spec["ref"] in existing_refs:
                continue

            dzones = zones_by_district.get(spec["district"], [])
            if not dzones:
                continue
            zone = dzones[spec["zone_idx"] % len(dzones)]

            onset_time = now + timedelta(hours=spec["onset_hours"])
            expires_time = now + timedelta(hours=spec["expires_hours"])

            approved_at = onset_time + timedelta(minutes=15) if spec.get("approved") or spec.get("delivered") else None
            approved_by = admin_user.id if approved_at else None

            rejected_at = onset_time + timedelta(minutes=25) if spec.get("rejected") else None
            rejected_by = admin_user.id if rejected_at else None

            cancelled_at = onset_time + timedelta(minutes=45) if spec.get("cancelled") or spec.get("all_clear") else None
            cancelled_by = admin_user.id if cancelled_at else None

            alert = Alert(
                reference=spec["ref"],
                zone_id=zone.id,
                severity=spec["severity"],
                status=spec["status"],
                headline=spec["headline"],
                reason=spec["reason"],
                instructions=spec["instructions"],
                onset=onset_time,
                expires=expires_time,
                geometry=zone.geometry,
                threatened_assets=[
                    {"name": f"{zone.name} Primary Corridor", "type": "ROAD", "exposure_score": 85},
                    {"name": f"{zone.name} Lower Settlement", "type": "SETTLEMENT", "population": 1420},
                ],
                source="BHUSHAKTI Early Warning Engine v0.9.0",
                disclaimer=ALERT_DISCLAIMER,
                template_version="tpl-v0.1",
                language="en",
                hazard_index=spec["hazard_index"],
                priority_level=spec["priority"],
                policy_version="policy-v0.1",
                is_scenario=False,
                created_by=analyst_user.id,
                created_at=onset_time,
                updated_at=now,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_by=rejected_by,
                rejected_at=rejected_at,
                rejection_reason=spec.get("rejection_reason"),
                cancelled_by=cancelled_by,
                cancelled_at=cancelled_at,
                cancel_reason=spec.get("cancel_reason"),
            )
            db.add(alert)
            db.flush()
            alerts_added += 1

            # Seed delivery records if DELIVERED or APPROVED
            if spec.get("delivered") or spec.get("approved"):
                for ch in ["SMS", "PUSH", "CAP_RSS"]:
                    deliv = AlertDelivery(
                        alert_id=alert.id,
                        channel=ch,
                        language="en",
                        status="DELIVERED" if spec.get("delivered") else "PENDING",
                        detail=json.dumps({"recipient_count": 850 if ch == "SMS" else 2400, "provider_ref": "CONF-9921"}),
                        template_version="tpl-v0.1",
                        delivered_at=now - timedelta(hours=spec["onset_hours"]) if spec.get("delivered") else None,
                        created_at=now - timedelta(hours=spec["onset_hours"]),
                    )
                    db.add(deliv)
                    deliveries_added += 1

        counts["alerts_added"] = alerts_added
        counts["deliveries_added"] = deliveries_added

        # =====================================================================
        # 2. RESPONSE ASSIGNMENTS (Response Center: DETECTED -> RESOLVED)
        # =====================================================================
        existing_assignments = db.execute(select(ResponseAssignment.id)).scalars().all()
        assignments_added = 0

        if len(existing_assignments) < 6:
            assignment_specs = [
                {
                    "district": "AS-KMR",
                    "zone_idx": 0,
                    "title": "Inspect Tension Crack Along Narakasur Bypass Culvert",
                    "priority": "P1",
                    "status": "DETECTED",
                    "assignee": None,
                    "notes": "Automated sensor trigger flagged 4 cm lateral displacement near culvert 14B.",
                    "reason": "Immediate life-safety verification needed before school bus transit window.",
                },
                {
                    "district": "ML-EKH",
                    "zone_idx": 1,
                    "title": "Evaluate Toe Erosion on Sohra Highway Retaining Structure",
                    "priority": "P2",
                    "status": "REVIEWED",
                    "assignee": field_user.id,
                    "notes": "Duty analyst reviewed drainage overflow report. Dispatched initial triage note.",
                    "reason": "Preventive geotechnical assessment requested by Meghalaya PWD.",
                },
                {
                    "district": "MZ-AIZ",
                    "zone_idx": 2,
                    "title": "Active Debris Clearance Assessment — Ramhlun North Slope",
                    "priority": "P1",
                    "status": "ASSIGNED",
                    "assignee": field_user.id,
                    "notes": "Field Officer tasked with UAV drone slope scan and inclinometer verification.",
                    "reason": "CRITICAL alert candidate generated. Field verification required for approval gate.",
                },
                {
                    "district": "AS-KMR",
                    "zone_idx": 3,
                    "title": "Ground Truth Inspection — Khanapara Hill Settlement Zone",
                    "priority": "P2",
                    "status": "INSPECTED",
                    "assignee": field_user.id,
                    "notes": "Field team completed GPS ground survey. Minor surficial soil slumping observed; bedrock intact.",
                    "reason": "Citizen mobile report verification.",
                },
                {
                    "district": "ML-EKH",
                    "zone_idx": 4,
                    "title": "Post-Monsoon Slope Stabilization Sign-Off — Cherrapunji Gorges",
                    "priority": "P3",
                    "status": "RESOLVED",
                    "assignee": analyst_user.id,
                    "notes": "Retaining net installation completed. Pore pressure sensor values normal. Signed off.",
                    "reason": "Routine hazard closure following civil mitigation works.",
                },
                {
                    "district": "MZ-AIZ",
                    "zone_idx": 5,
                    "title": "Reopened Assessment — Laipuitlang Subsidence Zone",
                    "priority": "P1",
                    "status": "REOPENED",
                    "assignee": field_user.id,
                    "notes": "Secondary rainfall event caused new ground fissures in previously cleared slope. Cadre re-deployed.",
                    "reason": "Fresh resident report of structural cracking in masonry retaining wall.",
                },
            ]

            for aspec in assignment_specs:
                dzones = zones_by_district.get(aspec["district"], [])
                zone = dzones[aspec["zone_idx"] % len(dzones)]
                ass = ResponseAssignment(
                    zone_id=zone.id,
                    title=aspec["title"],
                    priority=aspec["priority"],
                    status=aspec["status"],
                    assigned_to=aspec["assignee"],
                    assigned_by=admin_user.id,
                    notes=aspec["notes"],
                    reason=aspec["reason"],
                    due_at=now + timedelta(hours=12),
                    created_at=now - timedelta(hours=6),
                    updated_at=now - timedelta(hours=1),
                    closed_at=now - timedelta(hours=2) if aspec["status"] == "RESOLVED" else None,
                )
                db.add(ass)
                assignments_added += 1

        counts["assignments_added"] = assignments_added

        # =====================================================================
        # 3. NOTIFICATION LOGS (Notification Monitor)
        # =====================================================================
        existing_logs = db.execute(select(NotificationLog.id)).scalars().all()
        logs_added = 0

        if len(existing_logs) < 8:
            first_alert = db.execute(select(Alert)).scalars().first()
            alert_id = first_alert.id if first_alert else 1

            notif_specs = [
                {
                    "channel": "SMS_GOV_DLT",
                    "recipient": "Assam State Disaster Management Network (+91 94350 XXXXX - 1,240 contacts)",
                    "lang": "as",
                    "status": "DELIVERED",
                    "subject": "অসম চৰকাৰ: ভূ-স্খলনৰ জৰুৰী সতৰ্কবাৰ্তা",
                    "preview": "কামৰূপ মহানগৰ জিলাৰ পাহাৰীয়া অঞ্চলৰ বাবে গুৰুত্বপূৰ্ণ সতৰ্কবাৰ্তা...",
                    "retries": 1,
                    "ref": "DLT-AIRTEL-998241",
                },
                {
                    "channel": "FCM_APP_PUSH",
                    "recipient": "Registered Citizens — East Khasi Hills Geo-fence (4,120 devices)",
                    "lang": "kha",
                    "status": "DELIVERED",
                    "subject": "Khasi: Ka jingmahiar khndew ba jur",
                    "preview": "Sngewbha kynriah noh na ki jaka ba don ha kliar lum...",
                    "retries": 1,
                    "ref": "FCM-TOKEN-778210",
                },
                {
                    "channel": "SMS_GOV_DLT",
                    "recipient": "Aizawl District Emergency Response Volunteers (580 contacts)",
                    "lang": "miz",
                    "status": "PROCESSING",
                    "subject": "Mizo: Leimin hlauhthawnawm vawrh chhuah a ni",
                    "preview": "Ramhlun leh Laipuitlang biala chengte fimkhur tura hriattir in ni...",
                    "retries": 1,
                    "ref": "BSNL-QUEUE-4412",
                },
                {
                    "channel": "CAP_BROADCAST",
                    "recipient": "National Disaster Management Authority (NDMA) Integrated RSS Feed",
                    "lang": "en",
                    "status": "DELIVERED",
                    "subject": "CAP v1.2 XML Warning Broadcast — North East Pilot Region",
                    "preview": "Alert polygon geo-referenced to ISO 19115 schema...",
                    "retries": 1,
                    "ref": "CAP-NDMA-FED-8891",
                },
                {
                    "channel": "SMS_GOV_DLT",
                    "recipient": "Cherrapunji Highway Patrol Officers (45 contacts)",
                    "lang": "en",
                    "status": "PENDING",
                    "subject": "URGENT: SH-5 Slope Inspection Directive",
                    "preview": "Duty Officer: Deploy rapid patrol between km 18-22 immediately...",
                    "retries": 0,
                    "ref": None,
                },
                {
                    "channel": "SMS_GOV_DLT",
                    "recipient": "Remote Cell Tower Subscribers (Lower Subansiri Fringe)",
                    "lang": "en",
                    "status": "FAILED",
                    "subject": "Cell Tower Broadcast Attempt",
                    "preview": "Network timeout: BTS tower un-reachable due to localized power outage.",
                    "retries": 3,
                    "ref": "CARRIER-TIMEOUT-ERR-504",
                },
            ]

            for nspec in notif_specs:
                nlog = NotificationLog(
                    alert_id=alert_id,
                    channel=nspec["channel"],
                    recipient_target=nspec["recipient"],
                    language=nspec["lang"],
                    status=nspec["status"],
                    subject=nspec["subject"],
                    message_preview=nspec["preview"],
                    attempt_count=nspec["retries"],
                    max_retries=3,
                    provider_ref=nspec["ref"],
                    provider_confirmed_at=now - timedelta(minutes=10) if nspec["status"] == "DELIVERED" else None,
                    failure_reason="Carrier timeout (BTS backhaul fiber cut)" if nspec["status"] == "FAILED" else None,
                    escalation_level=1 if nspec["status"] != "FAILED" else 2,
                    created_at=now - timedelta(minutes=45),
                    updated_at=now,
                )
                db.add(nlog)
                logs_added += 1

        counts["logs_added"] = logs_added

        # =====================================================================
        # 4. SATELLITE CHANGE DETECTIONS (Satellite Change Dashboard)
        # =====================================================================
        existing_sat = db.execute(select(SatelliteChangeDetection.id)).scalars().all()
        sat_added = 0

        if len(existing_sat) < 4:
            sat_specs = [
                {
                    "district": "AS-KMR",
                    "source": "Sentinel-2 MSI Level-2A (10m Multi-spectral)",
                    "b_date": date.today() - timedelta(days=14),
                    "d_date": date.today() - timedelta(days=2),
                    "ndvi_drop": 42.5,
                    "area": 4200.0,
                    "lat": 26.155,
                    "lon": 91.765,
                    "conf": 88.5,
                    "status": "CANDIDATE_SCAR",
                    "notes": "Significant vegetation index plunge on steep south-facing cut-slope. Awaiting drone verification.",
                },
                {
                    "district": "ML-EKH",
                    "source": "PlanetScope Daily Ortho (3m High-Resolution)",
                    "b_date": date.today() - timedelta(days=7),
                    "d_date": date.today() - timedelta(days=1),
                    "ndvi_drop": 61.2,
                    "area": 12800.0,
                    "lat": 25.568,
                    "lon": 91.890,
                    "conf": 94.0,
                    "status": "VERIFIED_SCAR",
                    "notes": "Verified by SDRF Field Cadre ML-SDRF-01. Fresh crown scarp and debris runout fan confirmed.",
                },
                {
                    "district": "MZ-AIZ",
                    "source": "Sentinel-1 SAR C-Band InSAR Coherence",
                    "b_date": date.today() - timedelta(days=21),
                    "d_date": date.today() - timedelta(days=3),
                    "ndvi_drop": 18.0,
                    "area": 2500.0,
                    "lat": 23.732,
                    "lon": 92.715,
                    "conf": 45.0,
                    "status": "FALSE_POSITIVE",
                    "notes": "Analyst audit revealed agricultural terracing soil clearing, not a slope failure.",
                },
                {
                    "district": "ML-EKH",
                    "source": "Sentinel-2 MSI Level-2A (10m Multi-spectral)",
                    "b_date": date.today() - timedelta(days=10),
                    "d_date": date.today() - timedelta(days=2),
                    "ndvi_drop": 34.0,
                    "area": 3100.0,
                    "lat": 25.542,
                    "lon": 91.875,
                    "conf": 76.0,
                    "status": "UNDER_REVIEW",
                    "notes": "Optical change candidate flagged near SH-5 highway corridor. Dispatched field team for inspection.",
                },
            ]

            for sspec in sat_specs:
                dzones = zones_by_district.get(sspec["district"], [])
                zone = dzones[0] if dzones else zones[0]
                sdet = SatelliteChangeDetection(
                    district_code=sspec["district"],
                    zone_id=zone.id,
                    satellite_source=sspec["source"],
                    baseline_date=sspec["b_date"],
                    detection_date=sspec["d_date"],
                    ndvi_drop_pct=sspec["ndvi_drop"],
                    disturbance_area_m2=sspec["area"],
                    scar_lat=sspec["lat"],
                    scar_lon=sspec["lon"],
                    confidence_score=sspec["conf"],
                    status=sspec["status"],
                    candidate_incident_created=(sspec["status"] == "VERIFIED_SCAR"),
                    geometry_json={
                        "type": "Polygon",
                        "coordinates": [[
                            [sspec["lon"] - 0.002, sspec["lat"] - 0.002],
                            [sspec["lon"] + 0.002, sspec["lat"] - 0.002],
                            [sspec["lon"] + 0.002, sspec["lat"] + 0.002],
                            [sspec["lon"] - 0.002, sspec["lat"] + 0.002],
                            [sspec["lon"] - 0.002, sspec["lat"] - 0.002],
                        ]],
                    },
                    notes=sspec["notes"],
                    verified_by=analyst_user.id if sspec["status"] in ("VERIFIED_SCAR", "FALSE_POSITIVE") else None,
                    verified_at=now - timedelta(hours=12) if sspec["status"] in ("VERIFIED_SCAR", "FALSE_POSITIVE") else None,
                    created_at=now - timedelta(days=1),
                )
                db.add(sdet)
                sat_added += 1

        counts["sat_added"] = sat_added

        # =====================================================================
        # 5. FIELD & CITIZEN REPORTS (Field Ops: VERIFIED, REJECTED)
        # =====================================================================
        reports_added = 0
        existing_report_statuses = set(db.execute(select(Report.status)).scalars().all())

        if "VERIFIED" not in existing_report_statuses or "REJECTED" not in existing_report_statuses:
            report_specs = [
                {
                    "district": "AS-KMR",
                    "hazard": "SLOPE_MOVEMENT",
                    "status": "VERIFIED",
                    "desc": "Active ground crack of 15 cm width across village approach road with bulging toe.",
                    "notes": "Verified by Er. P. B. Sarma (AS-RRU-01). Controlled traffic barricade placed.",
                },
                {
                    "district": "ML-EKH",
                    "hazard": "ROCKFALL",
                    "status": "VERIFIED",
                    "desc": "Boulders collapsed onto SH-5 carriageway following heavy overnight rain.",
                    "notes": "Verified on-site. PWD excavator cleared lane 1.",
                },
                {
                    "district": "MZ-AIZ",
                    "hazard": "GROUND_CRACK",
                    "status": "REJECTED",
                    "desc": "Citizen reported foundation cracking on hillside house.",
                    "notes": "Inspection revealed superficial cement shrinkage crack; foundation bedrock stable.",
                },
            ]

            for r_idx, rspec in enumerate(report_specs):
                dzones = zones_by_district.get(rspec["district"], [])
                zone = dzones[r_idx % len(dzones)]
                rep = Report(
                    client_uuid=f"extra-seed-report-{rspec['district'].lower()}-{r_idx}",
                    zone_id=zone.id,
                    district_code=rspec["district"],
                    hazard_type=rspec["hazard"],
                    description=rspec["desc"],
                    lat=zone.centroid_lat + 0.001,
                    lon=zone.centroid_lon + 0.001,
                    gps_accuracy_m=8.5,
                    observed_at=now - timedelta(hours=10),
                    status=rspec["status"],
                    verification_note=rspec["notes"],
                    verified_at=now - timedelta(hours=4),
                    verified_by=field_user.id,
                    anonymous=False,
                    reporter_name="District Certified Field Cadre",
                    consent=True,
                    sync_source="online",
                )
                db.add(rep)
                reports_added += 1

        counts["reports_added"] = reports_added

        # =====================================================================
        # 6. HISTORICAL EVENT RECORDS (Historical Replay)
        # =====================================================================
        existing_hist = db.execute(select(HistoricalEventRecord.id)).scalars().all()
        hist_added = 0

        if not existing_hist:
            hist_episodes = [
                {
                    "district": "AS-KMR",
                    "date": date(2022, 6, 14),
                    "name": "Guwahati Urban Slope Crisis (June 2022)",
                    "rain24": 188.5,
                    "rain72": 342.0,
                    "hazard": 92.0,
                    "risk": "CRITICAL",
                    "slides": 14,
                    "fatalities": 4,
                    "displaced": 1200,
                    "roads": 3,
                    "damage": "Severe hillside collapses across Boragaon, Narakasur and Kharghuli ridges. NH-27 transit severed for 18 hours.",
                    "timeline": {
                        "00:00": "Rainfall onset (12 mm/h)",
                        "06:00": "Threshold breach (85 mm accumulated)",
                        "11:30": "First major slope movement recorded at Narakasur",
                        "15:00": "DDMA evacuation order executed for 450 residents",
                    },
                },
                {
                    "district": "ML-EKH",
                    "date": date(2023, 7, 21),
                    "name": "Sohra-Shella Escarpment Cloudburst Event (July 2023)",
                    "rain24": 310.0,
                    "rain72": 520.0,
                    "hazard": 96.5,
                    "risk": "CRITICAL",
                    "slides": 22,
                    "fatalities": 2,
                    "displaced": 850,
                    "roads": 4,
                    "damage": "Catastrophic debris flows along Sohra gorges. Multiple culverts washed out on SH-5.",
                    "timeline": {
                        "02:00": "Cloudburst onset over Cherrapunji plateau",
                        "07:00": "Warning escalated to CRITICAL",
                        "10:15": "Major debris flow blocked Mawkdok bridge access",
                        "16:00": "SDRF mountain rescue established emergency ropeway",
                    },
                },
                {
                    "district": "MZ-AIZ",
                    "date": date(2024, 5, 28),
                    "name": "Cyclone Remal Aizawl Slope Disasters (May 2024)",
                    "rain24": 224.0,
                    "rain72": 390.0,
                    "hazard": 94.0,
                    "risk": "CRITICAL",
                    "slides": 18,
                    "fatalities": 14,
                    "displaced": 2100,
                    "roads": 5,
                    "damage": "Melthum stone quarry collapse and Ramhlun hillside slips. City water supply pipes fractured.",
                    "timeline": {
                        "03:00": "Remal outer bands triggered intense rainfall",
                        "06:30": "Quarry slope failure at Melthum",
                        "09:00": "Civil hospital shelter fully activated",
                        "14:00": "National Highway 54 clearance ongoing",
                    },
                },
            ]

            for hspec in hist_episodes:
                hrec = HistoricalEventRecord(
                    district_code=hspec["district"],
                    event_date=hspec["date"],
                    event_name=hspec["name"],
                    rainfall_24h_mm=hspec["rain24"],
                    rainfall_72h_mm=hspec["rain72"],
                    max_hazard_index=hspec["hazard"],
                    predicted_risk_level=hspec["risk"],
                    verified_landslides_count=hspec["slides"],
                    fatalities=hspec["fatalities"],
                    displaced_persons=hspec["displaced"],
                    roads_blocked_count=hspec["roads"],
                    damage_summary=hspec["damage"],
                    timeline_snapshot=hspec["timeline"],
                    created_at=now,
                )
                db.add(hrec)
                hist_added += 1

        counts["hist_added"] = hist_added

        # =====================================================================
        # 7. EARLY WARNING TIMELINE EVENTS
        # =====================================================================
        existing_timeline = db.execute(select(EarlyWarningTimelineEvent.id)).scalars().all()
        timeline_added = 0

        if len(existing_timeline) < 10:
            target_zones = [zones[0], zones[1], zones[2]] if len(zones) >= 3 else zones
            for t_zone in target_zones:
                milestones = [
                    ("FIRST_DETECTED_RISK_INCREASE", -480, "BHUSHAKTI AI Kernel", {"rainfall_1h_mm": 18.2, "hazard_index": 28.5}, None, None),
                    ("WATCH_STATUS_ACTIVATED", -360, "Threshold Engine", {"threshold_breached": "WATCH", "hazard_index": 38.0}, 360, 85.0),
                    ("WARNING_STATUS_ACTIVATED", -240, "Threshold Engine", {"threshold_breached": "WARNING", "hazard_index": 64.5}, 240, 90.0),
                    ("CRITICAL_STATUS_ACTIVATED", -120, "Threshold Engine", {"threshold_breached": "CRITICAL", "hazard_index": 82.0}, 120, 92.0),
                    ("ALERT_CANDIDATE_GENERATED", -105, "Policy Engine", {"policy": "policy-v0.1", "reference": "ALT-2026-TIMELINE"}, 105, 95.0),
                    ("AUTHORITY_APPROVED", -75, "District Disaster Management Officer", {"reason": "Geotechnical sensor confirmation received"}, 75, 98.0),
                    ("NOTIFICATION_DISPATCHED", -60, "Carrier Gateway DLT", {"channels": ["SMS", "PUSH"], "recipients": 1420}, 60, 99.0),
                    ("FIELD_TEAM_DISPATCHED", -45, "State Response Coordinator", {"team_code": "AS-RRU-01", "cadre_size": 5}, 45, 95.0),
                    ("FIELD_INSPECTION_COMPLETED", -15, "Er. P. B. Sarma", {"findings": "Tension crack stabilized by sandbag berms"}, 15, 94.0),
                    ("INCIDENT_VERIFIED", -5, "Chief Geologist", {"status": "CONTROLLED", "post_inspection_score": 52.0}, 0, 96.0),
                ]
                for m_name, m_offset, actor_name, details, lead_time, eff_score in milestones:
                    ev = EarlyWarningTimelineEvent(
                        zone_id=t_zone.id,
                        alert_id=None,
                        milestone=m_name,
                        occurred_at=now + timedelta(minutes=m_offset),
                        actor_id=admin_user.id,
                        actor_name=actor_name,
                        details=details,
                        lead_time_minutes=lead_time,
                        effectiveness_score=eff_score,
                    )
                    db.add(ev)
                    timeline_added += 1

        counts["timeline_added"] = timeline_added

        # =====================================================================
        # 8. SENSORS & SENSOR READINGS (IoT Geotechnical Telemetry)
        # =====================================================================
        existing_sensors = db.execute(select(Sensor.id)).scalars().all()
        sensors_added = 0
        readings_added = 0

        if not existing_sensors:
            sensor_specs = [
                {"code": "SN-INC-01", "kind": "INCLINOMETER", "lat": 26.155, "lon": 91.772, "zone_idx": 0, "metric": "displacement_mm", "unit": "mm", "base_val": 4.2},
                {"code": "SN-PIEZ-02", "kind": "PIEZOMETER", "lat": 26.142, "lon": 91.765, "zone_idx": 1, "metric": "pore_water_pressure_kpa", "unit": "kPa", "base_val": 28.5},
                {"code": "SN-RAIN-03", "kind": "TIPPING_BUCKET", "lat": 25.572, "lon": 91.884, "zone_idx": 2, "metric": "precipitation_rate_mm_h", "unit": "mm/h", "base_val": 14.0},
                {"code": "SN-EXT-04", "kind": "EXTENSOMETER", "lat": 23.732, "lon": 92.719, "zone_idx": 3, "metric": "crack_aperture_mm", "unit": "mm", "base_val": 12.8},
            ]

            for s_spec in sensor_specs:
                z = zones[s_spec["zone_idx"] % len(zones)]
                sens = Sensor(
                    code=s_spec["code"],
                    kind=s_spec["kind"],
                    lat=s_spec["lat"],
                    lon=s_spec["lon"],
                    status="ACTIVE",
                    zone_id=z.id,
                    installed_at=now - timedelta(days=90),
                )
                db.add(sens)
                db.flush()
                sensors_added += 1

                # Add 6 hourly readings
                for h in range(6):
                    r_val = s_spec["base_val"] + (h * 0.4)
                    reading = SensorReading(
                        sensor_id=sens.id,
                        recorded_at=now - timedelta(hours=(5 - h)),
                        metric=s_spec["metric"],
                        value=round(r_val, 2),
                        unit=s_spec["unit"],
                    )
                    db.add(reading)
                    readings_added += 1

        counts["sensors_added"] = sensors_added
        counts["readings_added"] = readings_added

        # =====================================================================
        # 9. LANDSLIDE RUNOUT ZONES
        # =====================================================================
        existing_runout = db.execute(select(LandslideRunoutZone.id)).scalars().all()
        runout_added = 0

        if not existing_runout:
            runout_specs = [
                {
                    "district": "AS-KMR",
                    "zone_idx": 0,
                    "angle": 18.5,
                    "length": 450.0,
                    "area": 18500.0,
                    "slope": 38.0,
                    "flow_dir": 145.0,
                    "hazard": "HIGH",
                    "settlements": ["Narakasur Foot Settlement (Pop: 820)", "Bhangagarh Colony B (Pop: 450)"],
                    "roads": ["NH-27 Service Lane km 4", "Narakasur Approach Road"],
                },
                {
                    "district": "ML-EKH",
                    "zone_idx": 1,
                    "angle": 22.0,
                    "length": 820.0,
                    "area": 34000.0,
                    "slope": 44.0,
                    "flow_dir": 190.0,
                    "hazard": "VERY_HIGH",
                    "settlements": ["Sohra Lower Hamlet (Pop: 340)"],
                    "roads": ["State Highway 5 (Cherrapunji Corridor) km 18-20"],
                },
                {
                    "district": "MZ-AIZ",
                    "zone_idx": 2,
                    "angle": 19.8,
                    "length": 580.0,
                    "area": 22000.0,
                    "slope": 36.0,
                    "flow_dir": 210.0,
                    "hazard": "HIGH",
                    "settlements": ["Ramhlun Vengthlang Residential Sector (Pop: 1250)"],
                    "roads": ["Ramhlun Main Arterial Highway", "Bawngkawn Link Road"],
                },
            ]

            for rspec in runout_specs:
                dzones = zones_by_district.get(rspec["district"], [])
                z = dzones[rspec["zone_idx"] % len(dzones)]
                rzone = LandslideRunoutZone(
                    zone_id=z.id,
                    district_code=rspec["district"],
                    runout_angle_deg=rspec["angle"],
                    max_runout_length_m=rspec["length"],
                    affected_area_m2=rspec["area"],
                    slope_gradient_deg=rspec["slope"],
                    flow_direction_deg=rspec["flow_dir"],
                    runout_hazard_class=rspec["hazard"],
                    downslope_path_geojson={
                        "type": "LineString",
                        "coordinates": [
                            [z.centroid_lon, z.centroid_lat],
                            [z.centroid_lon + 0.003, z.centroid_lat - 0.003],
                            [z.centroid_lon + 0.006, z.centroid_lat - 0.005],
                        ],
                    },
                    threatened_settlements=rspec["settlements"],
                    threatened_roads=rspec["roads"],
                    generated_at=now,
                )
                db.add(rzone)
                runout_added += 1

        counts["runout_added"] = runout_added

        db.commit()
        log.info("Comprehensive seeding successfully completed: %s", counts)
        return counts

    except Exception as exc:
        db.rollback()
        log.error("Failed seeding sections: %s", exc, exc_info=True)
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = seed_all_sections()
    print("Seeding result:", res)
