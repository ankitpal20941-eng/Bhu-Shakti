# ADR 0004 — Exact log-odds attribution instead of SHAP

**Status:** accepted · **Date:** November 2026

## Context

The brief asks for explainability (SHAP). SHAP requires a fitted model and a background
distribution; computing SHAP values for expert-set weights would produce numbers that look
authoritative but describe a model that does not exist.

## Decision

Explain the static score by its exact additive decomposition:

```
z = Σ wᵢ · (xᵢ − μᵢ) / σᵢ
contributionᵢ = wᵢ · (xᵢ − μᵢ) / σᵢ
```

The API returns each term's log-odds and index effect, sorted by direction, with a narrative.
Rainfall, soil moisture, field evidence and coverage are reported separately and are explicitly
labelled as non-log-odds factors.

## Consequences

- The explanation is exactly consistent with the score (tested to 1e-5).
- No dependency on `shap`, no background dataset, no sampling noise.
- When a fitted model is released, real SHAP can replace this behind the same `drivers` shape;
  the UI does not need to change.
- We must keep saying "this is not SHAP" so nobody cites it as if it were.
