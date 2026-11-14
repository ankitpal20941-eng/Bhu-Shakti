"""Policy-based alert engine with mandatory human approval.

Flow: assessment -> candidate -> authority review -> approve/reject -> delivery.
Nothing is published publicly without an explicit approval recorded in
alert_approvals. Delivery adapters are explicit about their real state; there is
no fake "sent" status.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain import (
    ALERT_DISCLAIMER,
    AlertStatus,
    RiskLevel,
    risk_level_for,
)
from ..models import (
    Alert,
    AlertApproval,
    AlertDelivery,
    AlertPolicy,
    District,
    RiskAssessment,
    SpatialUnit,
    User,
)
from . import audit
from .events import bus
from .util import as_utc, iso

TEMPLATE_VERSION = "alert-tpl-v0.1"
REVIEWED_LANGUAGES = {"en"}
LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "as": "অসমীয়া (Assamese)",
    "bn": "বাংলা (Bengali)",
    "ne": "नेपाली (Nepali)",
}

INSTRUCTIONS = {
    "en": {
        "CRITICAL": (
            "Avoid travel on roads in and around the affected slope. Move away from steep slopes, "
            "hillside cuts and the toe of slopes. Follow instructions from the district administration "
            "and NDMA. Do not cross blocked or flooded roads. Report ground cracks to the control room."
        ),
        "WARNING": (
            "Stay alert for ground cracks, tilted trees, unusual water seepage and rockfall. Avoid "
            "unnecessary night travel on hill roads. Keep a family meeting point and emergency kit ready."
        ),
        "WATCH": (
            "Conditions are being monitored. Check official updates before travelling on hill roads "
            "and report any visible slope damage to your district control room."
        ),
        "SAFE": "No elevated hazard is currently indicated for this unit. Continue normal caution.",
    },
    "hi": {
        "CRITICAL": (
            "प्रभावित ढलान के आसपास की सड़कों पर यात्रा न करें। तीव्र ढलानों, पहाड़ी कटाव और ढलान के "
            "निचले हिस्से से दूर रहें। जिला प्रशासन और NDMA के निर्देशों का पालन करें। अवरुद्ध या "
            "बाढ़ग्रस्त सड़कों को पार न करें। जमीन की दरारें नियंत्रण कक्ष को बताएं।"
        ),
        "WARNING": (
            "जमीन की दरारें, झुके पेड़, असामान्य जल रिसाव और पत्थर गिरने पर ध्यान दें। पहाड़ी सड़कों "
            "पर रात की अनावश्यक यात्रा से बचें। परिवार के लिए मिलन स्थल और आपातकालीन किट तैयार रखें।"
        ),
        "WATCH": (
            "स्थिति की निगरानी की जा रही है। पहाड़ी सड़कों पर यात्रा से पहले आधिकारिक जानकारी देखें "
            "और ढलान में दिखने वाली क्षति की सूचना जिला नियंत्रण कक्ष को दें।"
        ),
        "SAFE": "इस इकाई के लिए अभी कोई बढ़ा हुआ खतरा संकेत नहीं है। सामान्य सावधानी रखें।",
    },
    "as": {
        "CRITICAL": (
            "প্ৰভাৱিত পাহাৰৰ ওচৰৰ পথত ভ্ৰমণ নকৰিব। খৰ ওলোমা পাহাৰ, পাহাৰ কটা অংশ আৰু পাহাৰৰ "
            "তলৰ অংশৰ পৰা আঁতৰি থাকক। জিলা প্ৰশাসন আৰু NDMA ৰ নিৰ্দেশনা মানি চলক। বন্ধ বা "
            "পানীৰে প্লাৱিত পথ নাপাৰ কৰিব। মাটিৰ ফাট জিলা নিয়ন্ত্ৰণ কক্ষত জনাওক।"
        ),
        "WARNING": (
            "মাটিৰ ফাট, হালি যোৱা গছ, অস্বাভাৱিক পানী ওলোৱা আৰু শিল বাগৰাৰ প্ৰতি সতৰ্ক থাকক। পাহাৰীয়া "
            "পথত ৰাতি অযথা ভ্ৰমণ এৰি চলক। পৰিয়ালৰ বাবে মিলন স্থান আৰু আপৎকালীন সঁজুলি সাজু ৰাখক।"
        ),
        "WATCH": (
            "পৰিস্থিতি পৰ্যবেক্ষণ কৰা হৈছে। পাহাৰীয়া পথত ভ্ৰমণৰ আগতে চৰকাৰী তথ্য চাওক আৰু দেখা "
            "ক্ষতিৰ কথা জিলা নিয়ন্ত্ৰণ কক্ষত জনাওক।"
        ),
        "SAFE": "এই এককৰ বাবে এতিয়া কোনো বৰ্ধিত বিপদৰ সংকেত নাই। সাধাৰণ সতৰ্কতা বজাই ৰাখক।",
    },
    "bn": {
        "CRITICAL": (
            "প্রভাবিত ঢালের আশেপাশের রাস্তায় ভ্রমণ করবেন না। খাড়া ঢাল, পাহাড়ি কাটা অংশ এবং ঢালের "
            "নিচের অংশ থেকে দূরে থাকুন। জেলা প্রশাসন ও NDMA-র নির্দেশ মেনে চলুন। বন্ধ বা জলমগ্ন রাস্তা "
            "পার হবেন না। মাটির ফাটল জেলা নিয়ন্ত্রণ কক্ষে জানান।"
        ),
        "WARNING": (
            "মাটির ফাটল, হেলে পড়া গাছ, অস্বাভাবিক জল seepage এবং পাথর পড়ার ব্যাপারে সতর্ক থাকুন। "
            "পাহাড়ি রাস্তায় রাতে অপ্রয়োজনীয় ভ্রমণ এড়িয়ে চলুন। পরিবারের জন্য মিলনস্থল ও "
            "জরুরি কিট প্রস্তুত রাখুন।"
        ),
        "WATCH": (
            "পরিস্থিতি পর্যবেক্ষণ করা হচ্ছে। পাহাড়ি রাস্তায় যাত্রার আগে সরকারি তথ্য দেখুন এবং "
            "দৃশ্যমান ক্ষতির কথা জেলা নিয়ন্ত্রণ কক্ষে জানান।"
        ),
        "SAFE": "এই ইউনিটের জন্য এখন কোনো বর্ধিত ঝুঁকির সংকেত নেই। স্বাভাবিক সতর্কতা বজায় রাখুন।",
    },
    "ne": {
        "CRITICAL": (
            "प्रभावित ढलान वरपरका सडकमा यात्रा नगर्नुहोस्। ठाडो ढलान, पहाड काटिएको भाग र ढलानको "
            "तल्लो भागबाट टाढा रहनुहोस्। जिल्ला प्रशासन र NDMA को निर्देशन पालना गर्नुहोस्। "
            "अवरुद्ध वा डुबान भएको सडक नतर्नुहोस्। जमिनको चिरा नियन्त्रण कक्षमा जानकारी गराउनुहोस्।"
        ),
        "WARNING": (
            "जमिनको चिरा, ढल्किएका रुख, असामान्य पानी चुहावट र ढुंगा खस्ने कुरामा सतर्क रहनुहोस्। "
            "पहाडी सडकमा राति अनावश्यक यात्रा नगर्नुहोस्। परिवारको भेट्ने स्थान र आपत्कालीन "
            "सामग्री तयार राख्नुहोस्।"
        ),
        "WATCH": (
            "अवस्था अनुगमन भइरहेको छ। पहाडी सडकमा यात्रा गर्नुअघि आधिकारिक जानकारी हेर्नुहोस् र "
            "देखिएको क्षति जिल्ला नियन्त्रण कक्षमा जानकारी गराउनुहोस्।"
        ),
        "SAFE": "यो इकाइका लागि अहिले कुनै बढेको जोखिम संकेत छैन। सामान्य सतर्कता अपनाउनुहोस्।",
    },
}


def severity_for(policy: AlertPolicy, hazard_index: float) -> RiskLevel:
    thresholds = policy.thresholds or {}
    if hazard_index >= float(thresholds.get("CRITICAL", 80)):
        return RiskLevel.CRITICAL
    if hazard_index >= float(thresholds.get("WARNING", 60)):
        return RiskLevel.WARNING
    return RiskLevel.WATCH


def active_policy(db: Session) -> AlertPolicy:
    policy = db.execute(
        select(AlertPolicy).where(AlertPolicy.active.is_(True)).order_by(AlertPolicy.created_at.desc())
    ).scalars().first()
    if policy:
        return policy
    return AlertPolicy(
        version="policy-v0.1-fallback",
        name="Fallback prototype policy",
        thresholds={"WATCH": 30, "WARNING": 60, "CRITICAL": 80},
        hysteresis_points=5.0,
        min_duration_min=0,
        dedupe_window_min=180,
        active=True,
    )


def _existing_active(db: Session, zone_id: int) -> Alert | None:
    return db.execute(
        select(Alert).where(
            Alert.zone_id == zone_id,
            Alert.is_scenario.is_(False),
            Alert.status.in_([AlertStatus.CANDIDATE, AlertStatus.APPROVED, AlertStatus.DELIVERED]),
        ).order_by(Alert.created_at.desc())
    ).scalars().first()


def new_reference(db: Session) -> str:
    while True:
        ref = f"BS-AL-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        if not db.execute(select(Alert).where(Alert.reference == ref)).scalars().first():
            return ref


def generate_candidates(
    db: Session,
    *,
    run_id: str,
    actor: dict[str, Any] | None,
    request_id: str,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Create alert candidates for units crossing the WARNING threshold."""
    now = now or datetime.now(timezone.utc)
    policy = active_policy(db)
    threshold = float((policy.thresholds or {}).get("WARNING", 60))
    created: list[dict[str, Any]] = []

    rows = db.execute(
        select(SpatialUnit, District, RiskAssessment)
        .join(District, SpatialUnit.district_code == District.code)
        .join(RiskAssessment, RiskAssessment.zone_id == SpatialUnit.id)
        .where(
            RiskAssessment.run_id == run_id,
            RiskAssessment.is_scenario.is_(False),
            RiskAssessment.hazard_index >= threshold,
        )
        .order_by(RiskAssessment.hazard_index.desc())
    ).all()

    for zone, district, assessment in rows:
        severity = severity_for(policy, assessment.hazard_index)
        existing = _existing_active(db, zone.id)
        if existing is not None:
            age_min = ((now - as_utc(existing.created_at)).total_seconds() / 60.0)
            if existing.severity == severity or (
                _rank(existing.severity) >= _rank(severity.value) and age_min <= policy.dedupe_window_min
            ):
                continue
            if _rank(severity.value) > _rank(existing.severity):
                # Escalation invalidates any prior approval: re-review is mandatory.
                previous = existing.severity
                existing.severity = severity.value
                existing.status = AlertStatus.CANDIDATE
                existing.approved_by = None
                existing.approved_at = None
                existing.hazard_index = assessment.hazard_index
                existing.updated_at = now
                db.add(AlertApproval(alert_id=existing.id, actor_id=(actor or {}).get("id"),
                                     action="ESCALATED",
                                     reason=f"Severity escalated {previous} -> {severity.value}; approval reset",
                                     at=now))
                audit.record(db, actor=actor, action="alert.escalated", entity="alert",
                             entity_id=existing.id, reason=f"{previous} -> {severity.value}",
                             payload={"hazard_index": assessment.hazard_index}, request_id=request_id)
                bus.publish("alert.updated", {"id": existing.id, "status": existing.status,
                                              "severity": existing.severity})
                created.append({"id": existing.id, "zone_id": zone.id, "action": "escalated",
                                "severity": severity.value})
                continue

        duration = _above_threshold_minutes(db, zone.id, threshold, now)
        if duration < policy.min_duration_min:
            continue

        instructions = INSTRUCTIONS["en"].get(severity.value, INSTRUCTIONS["en"]["WATCH"])
        drivers = assessment.drivers or {}
        top = (drivers.get("top_risk_increasing") or [{}])[0]
        reason = (
            f"Hazard index {assessment.hazard_index:.0f}/100 ({severity.value}) for {zone.name}. "
            f"Primary modelled driver: {top.get('label', 'terrain susceptibility')} "
            f"(about {abs(top.get('index_effect', 0)):.0f} index points). "
            f"Rainfall ratio vs prototype threshold: "
            f"{(assessment.inputs or {}).get('trigger', {}).get('combined_ratio', 'n/a')}. "
            f"Exposure {assessment.exposure_score:.0f}/100, operational priority {assessment.priority_level}. "
            "Hazard index is an uncalibrated prototype score, not a probability."
        )
        alert = Alert(
            reference=new_reference(db),
            zone_id=zone.id,
            severity=severity.value,
            status=AlertStatus.CANDIDATE,
            headline=f"{severity.value} landslide hazard — {zone.name}, {district.name} ({district.state})",
            reason=reason,
            instructions=instructions,
            onset=now,
            expires=now + timedelta(hours=6),
            geometry=zone.geometry,
            threatened_assets=[
                {"name": a.get("name"), "kind": a.get("kind"), "distance_km": a.get("distance_km")}
                for a in (assessment.inputs or {}).get("exposure", {}).get("assets", [])[:8]
            ],
            source=f"BHUSHAKTI AI {assessment.model_version} (candidate — requires authority approval)",
            disclaimer=ALERT_DISCLAIMER,
            template_version=TEMPLATE_VERSION,
            language="en",
            hazard_index=assessment.hazard_index,
            priority_level=assessment.priority_level,
            policy_version=policy.version,
            is_scenario=False,
            created_by=(actor or {}).get("id"),
        )
        db.add(alert)
        db.flush()
        db.add(AlertApproval(alert_id=alert.id, actor_id=(actor or {}).get("id"), action="CREATED",
                             reason="Generated by policy after threshold crossing", at=now))
        audit.record(db, actor=actor, action="alert.candidate_created", entity="alert",
                     entity_id=alert.id, reason=f"hazard {assessment.hazard_index:.1f} >= {threshold}",
                     payload={"reference": alert.reference, "severity": alert.severity},
                     request_id=request_id)
        bus.publish("alert.created", {"id": alert.id, "reference": alert.reference,
                                      "severity": alert.severity, "zone_id": zone.id})
        created.append({"id": alert.id, "reference": alert.reference, "zone_id": zone.id,
                        "severity": alert.severity, "action": "created"})

    expire_stale(db, now=now, actor=actor, request_id=request_id)
    return created


def _rank(severity: str) -> int:
    return {RiskLevel.WATCH.value: 1, RiskLevel.WARNING.value: 2, RiskLevel.CRITICAL.value: 3}.get(severity, 0)


def _above_threshold_minutes(db: Session, zone_id: int, threshold: float, now: datetime) -> int:
    from .risk import threshold_crossing_minutes

    rows = db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.zone_id == zone_id, RiskAssessment.is_scenario.is_(False))
        .order_by(RiskAssessment.computed_at.desc())
        .limit(50)
    ).scalars().all()
    if not rows:
        return 0
    earliest = as_utc(rows[0].computed_at)
    for row in rows:
        if row.hazard_index >= threshold:
            earliest = as_utc(row.computed_at)
        else:
            break
    return int((now - earliest).total_seconds() // 60)


def expire_stale(db: Session, *, now: datetime, actor: dict[str, Any] | None, request_id: str) -> int:
    rows = db.execute(
        select(Alert).where(
            Alert.status.in_([AlertStatus.APPROVED, AlertStatus.DELIVERED]),
            Alert.expires <= now,
            Alert.is_scenario.is_(False),
        )
    ).scalars().all()
    for alert in rows:
        alert.status = AlertStatus.EXPIRED
        alert.updated_at = now
        db.add(AlertApproval(alert_id=alert.id, actor_id=None, action="EXPIRED",
                             reason="Validity window elapsed", at=now))
        audit.record(db, actor=actor, action="alert.expired", entity="alert",
                     entity_id=alert.id, reason="validity window elapsed", request_id=request_id)
        bus.publish("alert.updated", {"id": alert.id, "status": alert.status})
    return len(rows)


# ---------------------------------------------------------------- workflow
def _deliveries_for(alert: Alert, languages: list[str]) -> list[AlertDelivery]:
    out: list[AlertDelivery] = []
    for language in languages:
        reviewed = language in REVIEWED_LANGUAGES
        for channel in ("in_app", "email", "sms"):
            if not reviewed:
                out.append(AlertDelivery(
                    alert_id=alert.id, channel=channel, language=language,
                    status="BLOCKED_UNREVIEWED_TEMPLATE",
                    detail="Translation is a machine-assisted draft and has not been reviewed by a native reviewer.",
                    template_version=TEMPLATE_VERSION,
                ))
                continue
            if channel == "in_app":
                out.append(AlertDelivery(
                    alert_id=alert.id, channel="in_app", language=language, status="DELIVERED",
                    detail="Recorded in the authority alert feed.", template_version=TEMPLATE_VERSION,
                    delivered_at=datetime.now(timezone.utc),
                ))
            elif channel == "email":
                out.append(AlertDelivery(
                    alert_id=alert.id, channel="email", language=language, status="QUEUED_NO_PROVIDER",
                    detail="Email adapter not configured (set BHUSHAKTI_EMAIL_PROVIDER). Nothing was sent.",
                    template_version=TEMPLATE_VERSION,
                ))
            else:
                out.append(AlertDelivery(
                    alert_id=alert.id, channel="sms", language=language, status="BLOCKED_NOT_CONFIGURED",
                    detail="No DLT-registered SMS provider configured; demo mode never sends SMS.",
                    template_version=TEMPLATE_VERSION,
                ))
    return out


def approve(
    db: Session,
    alert: Alert,
    *,
    actor: dict[str, Any],
    reason: str,
    languages: list[str] | None = None,
    request_id: str = "",
) -> dict[str, Any]:
    if alert.status not in {AlertStatus.CANDIDATE}:
        raise ValueError(f"Only CANDIDATE alerts can be approved (current: {alert.status})")
    if alert.is_scenario:
        raise ValueError("Scenario alerts are isolated and can never be approved or published")
    now = datetime.now(timezone.utc)
    languages = [lang for lang in (languages or ["en"]) if lang in LANGUAGES] or ["en"]
    alert.status = AlertStatus.APPROVED
    alert.approved_by = actor["id"]
    alert.approved_at = now
    alert.language = languages[0]
    alert.updated_at = now
    db.add(AlertApproval(alert_id=alert.id, actor_id=actor["id"], action="APPROVED", reason=reason, at=now))
    deliveries = _deliveries_for(alert, languages)
    for delivery in deliveries:
        db.add(delivery)
    if any(d.status == "DELIVERED" for d in deliveries):
        alert.status = AlertStatus.DELIVERED
    audit.record(db, actor=actor, action="alert.approved", entity="alert", entity_id=alert.id,
                 reason=reason, payload={"languages": languages,
                                         "deliveries": [{"channel": d.channel, "language": d.language,
                                                         "status": d.status} for d in deliveries]},
                 request_id=request_id)
    db.commit()
    bus.publish("alert.updated", {"id": alert.id, "status": alert.status, "severity": alert.severity})
    return {
        "id": alert.id,
        "status": alert.status,
        "approved_at": iso(alert.approved_at),
        "deliveries": [{"channel": d.channel, "language": d.language, "status": d.status,
                        "detail": d.detail} for d in deliveries],
    }


def reject(db: Session, alert: Alert, *, actor: dict[str, Any], reason: str, request_id: str = "") -> Alert:
    if alert.status not in {AlertStatus.CANDIDATE, AlertStatus.APPROVED}:
        raise ValueError(f"Cannot reject an alert in status {alert.status}")
    now = datetime.now(timezone.utc)
    alert.status = AlertStatus.REJECTED
    alert.rejected_by = actor["id"]
    alert.rejected_at = now
    alert.rejection_reason = reason
    alert.updated_at = now
    db.add(AlertApproval(alert_id=alert.id, actor_id=actor["id"], action="REJECTED", reason=reason, at=now))
    audit.record(db, actor=actor, action="alert.rejected", entity="alert", entity_id=alert.id,
                 reason=reason, request_id=request_id)
    db.commit()
    bus.publish("alert.updated", {"id": alert.id, "status": alert.status})
    return alert


def cancel(db: Session, alert: Alert, *, actor: dict[str, Any], reason: str, all_clear: bool = False,
           request_id: str = "") -> Alert:
    if alert.status in {AlertStatus.REJECTED, AlertStatus.EXPIRED, AlertStatus.CANCELLED,
                        AlertStatus.ALL_CLEAR}:
        raise ValueError(f"Alert already closed ({alert.status})")
    now = datetime.now(timezone.utc)
    alert.status = AlertStatus.ALL_CLEAR if all_clear else AlertStatus.CANCELLED
    alert.cancelled_by = actor["id"]
    alert.cancelled_at = now
    alert.cancel_reason = reason
    alert.updated_at = now
    db.add(AlertApproval(alert_id=alert.id, actor_id=actor["id"],
                         action="ALL_CLEAR" if all_clear else "CANCELLED", reason=reason, at=now))
    audit.record(db, actor=actor, action="alert.all_clear" if all_clear else "alert.cancelled",
                 entity="alert", entity_id=alert.id, reason=reason, request_id=request_id)
    db.commit()
    bus.publish("alert.updated", {"id": alert.id, "status": alert.status})
    return alert


def cap_message(alert: Alert, zone: SpatialUnit, district: District) -> dict[str, Any]:
    """CAP 1.2-shaped interoperable payload (not yet transmitted to any gateway)."""
    return {
        "identifier": alert.reference,
        "sender": "BHUSHAKTI AI (authority-approved)",
        "sent": iso(alert.updated_at),
        "status": "Actual",
        "msgType": "Alert",
        "scope": "Restricted",
        "info": [{
            "language": alert.language,
            "category": "Geo",
            "event": "Landslide",
            "urgency": "Immediate" if alert.severity == "CRITICAL" else "Expected",
            "severity": "Extreme" if alert.severity == "CRITICAL" else "Severe",
            "certainty": "Possible",
            "headline": alert.headline,
            "description": alert.reason,
            "instruction": alert.instructions,
            "onset": iso(alert.onset),
            "expires": iso(alert.expires),
            "area": {"areaDesc": f"{zone.name}, {district.name}, {district.state}",
                     "polygon": _polygon_string(alert.geometry)},
        }],
        "note": "Draft CAP mapping for future interoperability. Not sent to any gateway.",
    }


def _polygon_string(geometry: dict[str, Any] | None) -> str:
    try:
        ring = (geometry or {}).get("coordinates", [[]])[0]
        return " ".join(f"{lat},{lon}" for lon, lat in ring)
    except (IndexError, TypeError, ValueError):
        return ""
