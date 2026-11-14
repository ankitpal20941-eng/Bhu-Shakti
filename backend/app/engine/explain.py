"""Explainability: signed contributions, dominant drivers, and plain-language summary.

For the logistic susceptibility component the decomposition is EXACT (the terms
sum to the logit). For the noisy-OR combination and dynamic trigger we report
component deltas. Contributions are associative, not causal.
"""

from __future__ import annotations

from typing import Any

from .hazard import StaticResult, TriggerResult, _sigmoid
from . import params as P


def _delta_index(static: StaticResult, term_log_odds: float) -> float:
    """First-order effect of a log-odds term on the 0-100 susceptibility index."""
    p = static.probability_uncalibrated
    return 100.0 * p * (1.0 - p) * term_log_odds


def explain(
    *,
    static: StaticResult,
    trigger: TriggerResult,
    component_breakdown: dict[str, float],
    field_evidence: dict[str, Any],
    exposure: dict[str, Any],
    vulnerability_score: float,
    priority: dict[str, Any],
) -> dict[str, Any]:
    contributions: list[dict[str, Any]] = []
    for term in static.terms:
        delta = _delta_index(static, term["log_odds"])
        contributions.append({
            "key": term["key"],
            "label": term["label"],
            "value": term["value"],
            "log_odds": term["log_odds"],
            "index_effect": round(delta, 2),
            "direction": "increases" if delta >= 0 else "reduces",
            "provenance": term["provenance"],
        })

    # Dynamic trigger and field evidence are reported as their own block.
    trigger_delta = component_breakdown.get("dynamic_lift_points", 0.0)
    contributions.append({
        "key": "dynamic_trigger",
        "label": "Rainfall trigger",
        "value": round(trigger.index, 2),
        "log_odds": None,
        "index_effect": round(trigger_delta, 2),
        "direction": "increases" if trigger_delta >= 0 else "reduces",
        "provenance": "Live rainfall + soil moisture" if trigger.available else "Unavailable",
    })
    field_points = field_evidence.get("applied_points", 0.0)
    if field_points:
        contributions.append({
            "key": "field_evidence",
            "label": "Verified field evidence",
            "value": field_points,
            "log_odds": None,
            "index_effect": round(field_points, 2),
            "direction": "increases",
            "provenance": "Officer-verified reports (bounded, time-decayed)",
        })

    ranked = sorted(contributions, key=lambda c: abs(c["index_effect"]), reverse=True)
    increasing = [c for c in ranked if c["direction"] == "increases"][:5]
    reducing = [c for c in ranked if c["direction"] == "reduces"][:3]

    top = increasing[0] if increasing else None
    narrative_parts: list[str] = []
    if top:
        narrative_parts.append(
            f"Largest modelled contribution: {top['label']} ({top['value']} {_unit(top['key'])}) "
            f"adding about {top['index_effect']:.0f} points to the hazard index."
        )
    if trigger.available:
        narrative_parts.append(
            f"Rainfall is at {trigger.components.get('combined_ratio', 0)}× the prototype "
            f"intensity-duration threshold, contributing about {trigger_delta:.0f} points."
        )
    else:
        narrative_parts.append("Rainfall trigger is unavailable, so uncertainty is wider than usual.")
    if field_points:
        narrative_parts.append(f"Officer-verified field evidence adds {field_points:.0f} points (capped).")
    narrative_parts.append(
        f"Exposure index {exposure.get('score', 0):.0f} and vulnerability index "
        f"{vulnerability_score:.0f} are scored separately and combined only in the "
        f"operational priority ({priority.get('score', 0):.0f}, {priority.get('level', 'P4')})."
    )

    return {
        "contributions": ranked,
        "top_risk_increasing": increasing,
        "top_risk_reducing": reducing,
        "narrative": " ".join(narrative_parts),
        "attribution_method": (
            "Exact log-odds decomposition of the logistic susceptibility baseline, converted to "
            "index points by the logistic derivative; rainfall and field evidence are reported as "
            "component deltas. Contributions are associative, not causal."
        ),
        "model_note": (
            "Susceptibility weights are expert-set and uncalibrated. An SHAP explanation requires a "
            "model trained on a verified inventory; until then this additive decomposition is used."
        ),
        "model_version": P.MODEL_VERSION,
    }


def _unit(key: str) -> str:
    try:
        return P.PARAMS.feature(key).unit
    except KeyError:
        return ""


def static_term_table(static: StaticResult) -> dict[str, Any]:
    return {
        "intercept": P.INTERCEPT,
        "logit": static.logit,
        "sum_check": round(P.INTERCEPT + sum(t["log_odds"] for t in static.terms), 4),
        "terms": static.terms,
        "sigmoid": round(_sigmoid(static.logit), 6),
    }
