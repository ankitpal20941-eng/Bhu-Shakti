# Model card — `suscept-v0.1+trigger-v0.1`

| Field | Value |
| --- | --- |
| Version | `suscept-v0.1+trigger-v0.1` |
| Kind | Deterministic expert-parameterised index (not fitted) |
| Owner | BHUSHAKTI AI platform team (prototype) |
| Release date | Prototype, November 2026 |
| Status | `PROTOTYPE` — validation in progress |
| Trained | No |
| Calibrated | No |
| Output | Hazard index 0–100, hazard band, exposure, vulnerability, priority |
| Probability | **Not produced.** `hazard_probability = null`, `probability_status = NOT_CALIBRATED` |

## Intended use

- Ranking ~2 km planning units for inspection and preparedness inside the three pilot districts
  (Kamrup Metropolitan, East Khasi Hills, Aizawl).
- Explaining which terrain and rainfall factors drive a unit's score, in language an officer can
  check against local knowledge.
- Separating hazard from operational priority so that limited inspection capacity goes to units
  where something is actually exposed.
- Exercising the full workflow — candidate → human approval → delivery → response — during
  training and drills.

## Not intended for

- Public warning, evacuation orders, or any decision about an individual household.
- Insurance, land-use permitting, compensation or legal evidence.
- Ranking across states or outside the pilot districts (reference distribution does not apply).
- Real-time life-safety decisions without an authority's own information.
- Any claim of accuracy, skill, or probability of a landslide at a location.

## Inputs

| Group | Features | Provenance |
| --- | --- | --- |
| Terrain | slope, relief, curvature, elevation, TWI proxy, aspect wetness | Copernicus DEM GLO-90 sampled live via Open-Meteo at seed time |
| Land cover | land-cover factor | **SIMULATED** demo assignment |
| Geology | geology factor | **SIMULATED** demo assignment |
| Road cuts | proximity factor | Derived from indicative demo corridors |
| Rainfall | 1/6/24/72 h observations + 24 h forecast | Open-Meteo (LIVE) or simulated monsoon profile (SIMULATED, labelled) |
| Soil moisture | surface moisture % | Open-Meteo (LIVE) |
| Field evidence | verified reports, 14-day window | Officer-verified only |

## Validation state

```
method:        spatial-block + temporal holdout design (planned)
positives:     0 verified landslide records usable for fitting
negatives:     sampled non-events (not usable while positives are synthetic)
metrics:       {} — deliberately empty
blockers:      inventory synthetic; model untrained; method not yet executed;
               sample size below the minimum required by the gate
```

The validation gate (`engine/validation.py`, tested in `tests/test_validation.py`) refuses to
publish metrics when the inventory is synthetic, the model is untrained/uncalibrated, the method
is unsuitable, or the sample is too small. That is why the registry, analytics page and this card
show no numbers.

## Known limitations

1. **No calibration.** A score of 70 does not mean "70% chance". It means "higher than a score of
   50 under this prototype's ordering".
2. **Coarse DEM.** 90 m sampling at ~2.2 km grid spacing smooths local slopes; site-scale
   stability is not represented.
3. **Two simulated static features.** Land cover and geology are demo assignments; both carry
   real weight (0.60, 0.70) and can therefore move a unit's score materially.
4. **Global rainfall envelope.** Caine's envelope with an unvalidated 1.35 NER multiplier is a
   starting point, not a regional threshold calibrated on local landslides.
5. **Point rainfall.** District-centre grid values stand in for spatial rainfall; convective
   cells are much smaller than a district.
6. **No antecedent groundwater model.** Soil moisture is a surface proxy; deep pore pressure is
   not modelled.
7. **Inventory bias.** Reported landslides cluster near roads; absence of records is not absence
   of landslides.
8. **No road-cut inventory.** Proximity is a proxy for cut-slope disturbance, not a survey.
9. **English only.** Templates in other languages are drafts and are blocked from delivery.
10. **No drift monitoring.** No production feedback loop yet; recalibration must be manual.

## Ethical and governance considerations

- The index must not be presented to citizens as a warning. The citizen portal shows only
  plain-language level, reasons, and *approved* advisories.
- District scoping prevents an operator in one district from reading another district's reports.
- Reports are consent-gated for GPS and media, and are never published individually.
- Model changes require a new version, a card update and a recorded approval; the registry
  refuses to activate a version with no executable implementation.

## Monitoring (planned, not implemented)

Population stability of each feature, share of units out of domain, share of assessments with
STALE/SIMULATED weather, alert approval latency, false-alarm review rate after the monsoon, and
inventory growth. No dashboards for these exist yet; the analytics page shows the operational
counters that are available.

## Release criteria for a successor version

1. Verified inventory with ≥ 3 monsoon seasons and documented provenance.
2. Spatial block CV + temporal holdout, with PR-AUC and a reliability curve recorded.
3. Calibration applied and `probability_status` set to `CALIBRATED`.
4. Feature provenance upgraded (land cover and geology no longer simulated).
5. Model card, methodology and drift plan reviewed and signed off.
6. Activation through the registry, with rollback to the previous version tested.
