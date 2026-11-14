"""Validation harness.

Metrics are implemented for real; the GATE decides whether they may be shown as
evidence of model performance. A prototype with expert-set weights and a
synthetic inventory can never pass the gate, so the product shows
"VALIDATION IN PROGRESS" instead of invented accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

PUBLISHABLE_METHODS = {"SPATIAL_BLOCK_CV", "TEMPORAL_HOLDOUT", "PROSPECTIVE_SHADOW"}
MIN_EVENTS = 30
MIN_NON_EVENTS = 30


@dataclass
class BinaryScores:
    y_true: Sequence[int]
    y_score: Sequence[float]


def _validate(scores: BinaryScores) -> None:
    if len(scores.y_true) != len(scores.y_score):
        raise ValueError("y_true and y_score must have equal length")
    if not scores.y_true:
        raise ValueError("empty evaluation set")
    if any(v not in (0, 1) for v in scores.y_true):
        raise ValueError("y_true must be binary")


def confusion(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, float]:
    c = confusion(y_true, y_pred)
    precision = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alarm_ratio": round(c["fp"] / (c["fp"] + c["tn"]), 4) if (c["fp"] + c["tn"]) else 0.0,
        "missed_event_rate": round(c["fn"] / (c["fn"] + c["tp"]), 4) if (c["fn"] + c["tp"]) else 0.0,
    }


def roc_auc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    """Rank-based AUC (Mann-Whitney U), ties handled with average ranks."""
    positives = [s for t, s in zip(y_true, y_score) if t == 1]
    negatives = [s for t, s in zip(y_true, y_score) if t == 0]
    if not positives or not negatives:
        return 0.0
    order = sorted(range(len(y_score)), key=lambda i: y_score[i])
    ranks = [0.0] * len(y_score)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and y_score[order[j + 1]] == y_score[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    rank_sum = sum(r for r, t in zip(ranks, y_true) if t == 1)
    n_pos, n_neg = len(positives), len(negatives)
    return round((rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg), 4)


def average_precision(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    pairs = sorted(zip(y_score, y_true), key=lambda p: p[0], reverse=True)
    tp = 0
    fp = 0
    prev_recall = 0.0
    ap = 0.0
    total_pos = sum(y_true)
    if total_pos == 0:
        return 0.0
    for _, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        recall = tp / total_pos
        precision = tp / (tp + fp)
        ap += precision * (recall - prev_recall)
        prev_recall = recall
    return round(ap, 4)


def brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    return round(sum((p - t) ** 2 for t, p in zip(y_true, y_prob)) / len(y_true), 4)


def reliability(y_true: Sequence[int], y_prob: Sequence[float], bins: int = 5) -> list[dict[str, float]]:
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for t, p in zip(y_true, y_prob):
        idx = min(bins - 1, int(max(0.0, min(0.999999, p)) * bins))
        buckets[idx].append((p, t))
    out = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        out.append({
            "bin": f"{i / bins:.1f}-{(i + 1) / bins:.1f}",
            "n": len(bucket),
            "mean_predicted": round(sum(p for p, _ in bucket) / len(bucket), 4),
            "observed_rate": round(sum(t for _, t in bucket) / len(bucket), 4),
        })
    return out


def spatial_block_cv(records: Iterable[dict[str, Any]], block_deg: float = 0.25) -> list[dict[str, Any]]:
    """Group records into spatial blocks so folds do not leak neighbouring cells."""
    blocks: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for rec in records:
        key = (int(rec["lat"] // block_deg), int(rec["lon"] // block_deg))
        blocks.setdefault(key, []).append(rec)
    return [{"block": f"{k[0]}:{k[1]}", "records": v} for k, v in blocks.items()]


def run_validation(
    *,
    records: Sequence[dict[str, Any]],
    method: str,
    inventory_is_synthetic: bool,
    model_trained: bool,
    model_calibrated: bool,
    threshold: float = 60.0,
) -> dict[str, Any]:
    """Evaluate only when the evidence can support a published metric.

    Returns a status and, when allowed, metric values. In every other case the
    product displays VALIDATION IN PROGRESS with the specific blocking reason.
    """
    n_pos = sum(1 for r in records if r.get("label") == 1)
    n_neg = len(records) - n_pos
    blockers: list[str] = []
    if inventory_is_synthetic:
        blockers.append("The only available inventory is simulated demonstration data.")
    if not model_trained:
        blockers.append("Active model uses expert-set prototype weights, not fitted parameters.")
    if not model_calibrated:
        blockers.append("Hazard output is not calibrated to observed event frequency.")
    if n_pos < MIN_EVENTS:
        blockers.append(f"Only {n_pos} verified events available (minimum {MIN_EVENTS}).")
    if n_neg < MIN_NON_EVENTS:
        blockers.append(f"Only {n_neg} sampled non-events available (minimum {MIN_NON_EVENTS}).")
    if method not in PUBLISHABLE_METHODS:
        blockers.append(f"Validation design '{method}' cannot support generalisation claims.")

    base = {
        "method": method,
        "n_records": len(records),
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "threshold": threshold,
        "blocks": len(spatial_block_cv(records)),
        "model_trained": model_trained,
        "model_calibrated": model_calibrated,
        "inventory_is_synthetic": inventory_is_synthetic,
    }
    if blockers:
        return {**base, "status": "VALIDATION_IN_PROGRESS", "publishable": False, "blockers": blockers}

    labels = [int(r["label"]) for r in records]
    scores = [float(r["score"]) for r in records]
    preds = [1 if s >= threshold else 0 for s in scores]
    return {
        **base,
        "status": "COMPLETE",
        "publishable": True,
        "blockers": [],
        "metrics": {
            **precision_recall_f1(labels, preds),
            "roc_auc": roc_auc(labels, scores),
            "pr_auc": average_precision(labels, scores),
            "brier": brier_score(labels, [s / 100.0 for s in scores]),
            "reliability": reliability(labels, [s / 100.0 for s in scores]),
            "confusion": confusion(labels, preds),
        },
    }
