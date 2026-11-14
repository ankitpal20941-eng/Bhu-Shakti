"""Validation metrics + the gate that forbids publishing unearned metrics."""

from __future__ import annotations

from app.engine.validation import (
    average_precision,
    brier_score,
    confusion,
    precision_recall_f1,
    reliability,
    roc_auc,
    run_validation,
    spatial_block_cv,
)


def test_perfect_ranking_auc():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0


def test_tied_scores_give_half_auc():
    assert roc_auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_average_precision_perfect_and_baseline():
    assert average_precision([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]) == 1.0
    assert 0.0 <= average_precision([1, 0, 1, 0], [0.5, 0.4, 0.3, 0.2]) <= 1.0


def test_confusion_and_rates():
    metrics = precision_recall_f1([1, 1, 0, 0], [1, 0, 0, 1])
    assert confusion([1, 1, 0, 0], [1, 0, 0, 1]) == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["false_alarm_ratio"] == 0.5
    assert metrics["missed_event_rate"] == 0.5


def test_brier_and_reliability_inputs():
    assert brier_score([1, 0], [1.0, 0.0]) == 0.0
    bins = reliability([1, 0, 1, 0], [0.9, 0.8, 0.2, 0.1], bins=5)
    assert len(bins) == 3
    assert all("observed_rate" in b for b in bins)


def test_spatial_blocks_are_distinct():
    records = [{"lat": 25.5, "lon": 91.9}, {"lat": 25.51, "lon": 91.91}, {"lat": 26.2, "lon": 92.4}]
    blocks = spatial_block_cv(records, block_deg=0.25)
    assert len(blocks) == 2
    assert sum(len(b["records"]) for b in blocks) == 3


def test_gate_blocks_synthetic_inventory():
    records = [{"label": i % 2, "score": 50 + i, "lat": 25.5, "lon": 91.9} for i in range(100)]
    result = run_validation(
        records=records, method="SPATIAL_BLOCK_CV",
        inventory_is_synthetic=True, model_trained=False, model_calibrated=False,
    )
    assert result["status"] == "VALIDATION_IN_PROGRESS"
    assert result["publishable"] is False
    assert "metrics" not in result
    assert any("simulated" in b.lower() for b in result["blockers"])


def test_gate_blocks_random_split():
    records = [{"label": i % 2, "score": 50 + i, "lat": 25.5, "lon": 91.9} for i in range(100)]
    result = run_validation(
        records=records, method="RANDOM_SPLIT",
        inventory_is_synthetic=False, model_trained=True, model_calibrated=True,
    )
    assert result["publishable"] is False


def test_gate_allows_publishable_design():
    records = [
        {"label": 1 if i % 3 == 0 else 0, "score": 30 + (i % 60), "lat": 25.4 + (i % 5) * 0.2,
         "lon": 91.8 + (i % 7) * 0.2}
        for i in range(120)
    ]
    result = run_validation(
        records=records, method="SPATIAL_BLOCK_CV",
        inventory_is_synthetic=False, model_trained=True, model_calibrated=True,
    )
    assert result["status"] == "COMPLETE"
    assert result["publishable"] is True
    assert "roc_auc" in result["metrics"]
