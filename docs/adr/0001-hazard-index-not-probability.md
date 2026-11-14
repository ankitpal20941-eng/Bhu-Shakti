# ADR 0001 — Publish a hazard index, not a probability

**Status:** accepted · **Date:** November 2026

## Context

The product brief asks for landslide early warning with "confidence" and percentages. Producing a
probability requires a fitted model, a verified inventory, calibration and a base rate. None
exist for this build. Displaying a percentage would create false authority in a life-safety
context.

## Decision

- The engine emits a 0–100 index, bands (`SAFE/WATCH/WARNING/CRITICAL`) and an explicit
  `probability_status = NOT_CALIBRATED` with `hazard_probability = null`.
- Every API payload, screen, export and document states that the index is uncalibrated.
- Metrics stay empty until a validated model is released through the registry.

## Consequences

- The UI cannot show "70% chance"; it shows a band, a score, the drivers and the coverage.
- Calibration becomes a gated release criterion rather than a cosmetic field.
- Some stakeholders will find the output less familiar; the explanation panel and this
  documentation compensate by being specific about what the number is.
