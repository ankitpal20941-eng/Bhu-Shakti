"""Early Warning Timeline and Decision Audit Engine.

Tracks milestone progressions for monitored risk zones from sensing through verification:
- Computes warning lead time, response latency, and operational effectiveness
- Preserves timestamped audit trail of human decisions vs automated alerts
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def calculate_timeline_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculates operational performance metrics from chronological timeline milestones."""
    if not events:
        return {
            "warning_lead_time_hours": None,
            "decision_latency_minutes": None,
            "dispatch_latency_minutes": None,
            "overall_effectiveness_score": None,
            "milestone_count": 0,
        }

    sorted_events = sorted(events, key=lambda e: e.get("occurred_at") or "")

    by_type = {e.get("milestone"): e for e in sorted_events}

    # 1. Decision Latency: ALERT_GENERATED -> ALERT_APPROVED
    gen = by_type.get("ALERT_GENERATED")
    appr = by_type.get("ALERT_APPROVED")
    decision_min = None
    if gen and appr:
        t_gen = datetime.fromisoformat(str(gen["occurred_at"]).replace("Z", "+00:00"))
        t_appr = datetime.fromisoformat(str(appr["occurred_at"]).replace("Z", "+00:00"))
        decision_min = max(0, int((t_appr - t_gen).total_seconds() / 60.0))

    # 2. Dispatch Latency: ALERT_APPROVED -> TEAM_ASSIGNED
    assign = by_type.get("TEAM_ASSIGNED")
    dispatch_min = None
    if appr and assign:
        t_appr = datetime.fromisoformat(str(appr["occurred_at"]).replace("Z", "+00:00"))
        t_assign = datetime.fromisoformat(str(assign["occurred_at"]).replace("Z", "+00:00"))
        dispatch_min = max(0, int((t_assign - t_appr).total_seconds() / 60.0))

    # 3. Warning Lead Time: NOTIFICATION_DELIVERED -> INCIDENT_OCCURRED (or peak hazard)
    deliv = by_type.get("NOTIFICATION_DELIVERED")
    inc = by_type.get("INCIDENT_OCCURRED") or by_type.get("CRITICAL_TRIGGERED")
    lead_time_hrs = None
    if deliv and inc:
        t_deliv = datetime.fromisoformat(str(deliv["occurred_at"]).replace("Z", "+00:00"))
        t_inc = datetime.fromisoformat(str(inc["occurred_at"]).replace("Z", "+00:00"))
        lead_time_hrs = round((t_inc - t_deliv).total_seconds() / 3600.0, 1)

    # 4. Effectiveness score (0 to 100)
    score = 75.0
    if decision_min is not None and decision_min <= 20:
        score += 10.0
    if lead_time_hrs is not None and lead_time_hrs >= 4.0:
        score += 15.0

    return {
        "warning_lead_time_hours": lead_time_hrs,
        "decision_latency_minutes": decision_min,
        "dispatch_latency_minutes": dispatch_min,
        "overall_effectiveness_score": min(100.0, score),
        "milestone_count": len(sorted_events),
    }
