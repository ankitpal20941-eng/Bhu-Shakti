# ML methodology

**This document describes a prototype, not a validated model.** Every coefficient was set by
expert judgement. No coefficient was fitted to a verified landslide inventory, and no metric in
this document is a measured performance figure. `PARAMS.trained = False`,
`PARAMS.calibrated = False`, `hazard_probability = null`, `probability_status = NOT_CALIBRATED`.

## 1. Why an index instead of a probability

A probability requires (a) a fitted model, (b) a verified inventory with dates and locations,
(c) calibration on held-out data, and (d) a stable base rate for the area. This build has none of
those at the required quality, so publishing "34% chance of a landslide" would be fabrication.
Instead the engine emits a **0–100 hazard index** that is monotone in the physical drivers and is
explicitly labelled uncalibrated in every payload, screen and exported file.

## 2. Susceptibility (static, `suscept-v0.1`)

```
z = b0 + Σ wᵢ · (xᵢ − μᵢ) / σᵢ
S = 100 / (1 + e^(−z)),   b0 = 0
```

`μ, σ` are the observed mean and standard deviation of the 116 pilot units (November 2026 DEM
sampling plus demo land-cover/geology assignment). They only standardise units; they are not
fitted coefficients.

| Feature | Weight | Source | Note |
| --- | --- | --- | --- |
| Slope angle | 0.95 | DEM (live) | Dominant driver |
| Terrain relief (ruggedness) | 0.45 | DEM (live) | Elevation range in the sampled cell |
| Profile curvature | 0.25 | DEM (live) | Concave hollows collect water |
| Elevation | 0.15 | DEM (live) | Weak association in NER |
| Topographic wetness index | 0.30 | DEM proxy (live) | Approximated from slope; contributing area not modelled |
| Aspect wetness | 0.25 | DEM (live) | South/south-west aspects wetter in monsoon |
| Land-cover factor | 0.60 | Demo assignment (SIMULATED) | Replace with ESA WorldCover |
| Geology factor | 0.70 | Demo assignment (SIMULATED) | Replace with GSI lithology |
| Road-cut proximity | 0.40 | Indicative demo corridors | Cut slopes destabilise hillsides |

Land-cover and geology use lookup factors (`LANDSLIDE_TYPE_FACTORS`, `GEOLOGY_FACTORS`), not
learned embeddings. Because two of nine features are demo-assigned, susceptibility is *partly*
simulated in this build and the data-health screen says so.

## 3. Trigger (dynamic, `trigger-v0.1`)

Intensity–duration envelope after Caine (1980):

```
I = 14.82 · D^(−0.39) · 1.35        [mm/h, hours]
```

The 1.35 regional multiplier is a prototype assumption for the NER monsoon and is **not**
validated for these districts.

For each window (1, 6, 24, 72 h) the observed intensity is compared with the envelope at that
duration; the 24 h forecast adds a fifth ratio:

```
ratio_d = I_d / I_envelope(d)
combined = Σ ratio_d · w_d,  w = {1h:0.15, 6h:0.25, 24h:0.30, 72h:0.15, fc24:0.15}
T = 100 · clip(combined / 2.0, 0, 1) · soil_factor · season_factor
```

- `soil_factor` rises linearly from 1.0 at 20% moisture to 1.30 at 60%.
- `season_factor` is 0.85 outside May–October.
- If no usable weather exists, `T` is set to the mid-range 50 and the hazard is multiplied by
  0.50; coverage drops and the UI states that weather is unavailable.

## 4. Combination

```
hazard = 100 · (S/100) · (0.20 + 0.80 · T/100)
```

Why multiplicative rather than noisy-OR: an additive/noisy-OR form saturated near 100 whenever
several inputs were moderately high, which made the ranking useless. The multiplicative form
says a steep, wet slope is high hazard, while a steep dry slope is *primed* but not currently
hazardous. `TRIGGER_FLOOR = 0.20` keeps a residual so "no rain" is not literally zero.

Bands (prototype, configurable): `WATCH ≥ 30`, `WARNING ≥ 60`, `CRITICAL ≥ 80`.

## 5. Field evidence

Verified reports within 14 days contribute points weighted by hazard type
(`SLOPE_MOVEMENT` 8, `DEBRIS_FLOW` 8, `GROUND_CRACK` 6, `SUBSIDENCE` 6, `ROCKFALL` 5,
`ROAD_BLOCKAGE` 3, `OTHER` 2), decaying with a 7-day half-life and capped at +15 points. Only
`VERIFIED` reports count; `PENDING_VERIFICATION` and `REJECTED` never do. The applied points and
cap are stored with the assessment.

## 6. Exposure, vulnerability, priority

```
exposure = 100 · min(1, Σ asset_weight + 0.5·road_km + 0.002·population_k / 12)
vulnerability = 100 · (0.30·settlement_density + 0.25·road_dependency
                     + 0.20·emergency_access_gap + 0.15·landcover_sensitivity
                     + 0.10·population_share)
priority = 0.60·hazard + 0.25·exposure + 0.15·vulnerability
```

Priority bands: P1 ≥ 75 (IMMEDIATE), P2 ≥ 55 (URGENT), P3 ≥ 35 (MONITOR), P4 (ROUTINE).
Exposure assets within 2.5 km of the unit centroid: bridges 1.0, hospitals 1.0, settlements 0.8,
schools 0.6, plus road length and population terms.

Priority is an **operational ranking**, not a second hazard statement. A CRITICAL-hazard unit with
no exposed assets can be P3; that is the intended behaviour and is explained in the drawer.

## 7. Explanation

Attribution is the **exact decomposition of the logistic log-odds**:

```
contributionᵢ = wᵢ · (xᵢ − μᵢ) / σᵢ
z = Σ contributionᵢ
```

The `drivers` payload lists each term's log-odds and its index effect, sorted by direction. This
is not SHAP: SHAP requires a fitted model with a background distribution, and computing it here
would imply a model that does not exist. Rainfall, soil moisture, field evidence and coverage are
reported as separate, explicitly non-log-odds factors.

## 8. Trajectory

For each horizon (6, 12, 24, 48 h) the engine re-runs the trigger with the forecast rainfall
attached to that horizon and keeps the same susceptibility. If a horizon has no forecast, it is
returned in `unavailable_horizons` with a reason instead of a fabricated value. Forecast
trajectories are labelled as such and are never converted to probability.

## 9. Coverage

Coverage is a **rule-based checklist**, not a confidence score:

| Item | Points |
| --- | --- |
| Weather live and fresh | 3 |
| Weather live but aged | 2 |
| Weather cached | 1 |
| Soil moisture live | 1 |
| Terrain from live DEM | 2 |
| Verified inventory present | 1 |
| Authoritative land cover | 1 |

HIGH ≥ 6, MEDIUM ≥ 3, else LOW, with reasons listed per item.

## 10. Validation plan (not yet executed)

1. Assemble a verified inventory for the three districts (date, location, type, source,
   verification). The current inventory is synthetic and cannot be used.
2. Fit susceptibility with spatial block cross-validation (blocks ≥ 10 km) to avoid leakage.
3. Hold out the most recent monsoon season temporally.
4. Evaluate discrimination (PR-AUC, ROC-AUC), calibration (reliability curve, Brier score) and
   operational lift (precision at the top-k units a district can actually inspect).
5. Calibrate with isotonic/Platt scaling; only then populate `metrics` and set
   `probability_status = CALIBRATED`.
6. Re-run the validation gate, which refuses to publish until all of the above is recorded.

Until then `MODEL_CARD.md` states "no measured performance" and the UI says the same.
