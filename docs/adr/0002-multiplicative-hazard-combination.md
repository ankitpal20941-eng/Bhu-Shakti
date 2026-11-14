# ADR 0002 — Multiplicative hazard combination

**Status:** accepted · **Date:** November 2026

## Context

The first implementation combined susceptibility and trigger with a noisy-OR. With several
moderately high inputs the result saturated near 100, so a steep dry slope and a steep saturated
slope looked almost identical. That destroyed the ranking the districts actually use.

## Decision

```
hazard = 100 · (S/100) · (0.20 + 0.80 · T/100)
```

Hazard is susceptibility gated by trigger activation. `TRIGGER_FLOOR = 0.20` keeps a residual so
"no rain" is not literally zero. When weather is unavailable, the trigger is set to 50 and the
result multiplied by 0.50, and coverage is reduced.

## Consequences

- A highly susceptible but dry unit is "primed", not "critical", which matches field intuition.
- Heavy rain on flat terrain stays low (no saturation), so the top of the ranking is meaningful.
- The combination is explainable in one sentence, and the constants are documented in
  `ML_METHODOLOGY.md`.
- The floor and multiplier are prototype choices and must be revisited with a fitted model.
