# Risk-model validation

This page records the output of `python risk_model/trouver_crues.py <zone>`
run locally on 29 October 2026 with the cached Open-Meteo/GloFAS history and
the locally trained model.

The command reports the largest simulated annual peaks available in the cache.
The tables below focus on peaks in the held-out test period (2020 onward) and
also include the explicitly required 2017 check. Scores are probabilities in
the range 0-1.

## Verdict rule

- **retrieved**: at least one pre-peak score is medium or high, without the
  river already being above the flood threshold at all reported checkpoints.
- **missed**: all reported pre-peak scores are low.
- **already ongoing**: at least one reported checkpoint is already classified
  as `crue en cours` (score 1.000 because the threshold has already been
  crossed).

This is a diagnostic replay, not a claim that every flood event was detected.
The annual-peak list is selected by the existing script and is not an
independent hydrological ground truth.

## Test-period peaks (2020 onward)

| Zone | Peak date | Modelled peak discharge | J-7 | J-5 | J-3 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Betérou | 2020-09-11 | 479 m³/s | 0.493 (medium) | 0.435 (medium) | 1.000 (ongoing) | already ongoing |
| Betérou | 2022-09-22 | 606 m³/s | 1.000 (ongoing) | 1.000 (ongoing) | 1.000 (ongoing) | already ongoing |
| Bonou | 2022-09-23 | 1373 m³/s | 1.000 (ongoing) | 1.000 (ongoing) | 1.000 (ongoing) | already ongoing |
| Porto-Novo | 2022-09-24 | 1395 m³/s | 1.000 (ongoing) | 1.000 (ongoing) | 1.000 (ongoing) | already ongoing |
| Adjohoun | 2022-09-23 | 1373 m³/s | 1.000 (ongoing) | 1.000 (ongoing) | 1.000 (ongoing) | already ongoing |
| Dangbo | 2022-09-23 | 1373 m³/s | 1.000 (ongoing) | 1.000 (ongoing) | 1.000 (ongoing) | already ongoing |

## Explicit 2017 check

The 2017 peak is in the validation period, not the held-out test period. It is
included because it is an important failure case.

| Zone | Peak date | Modelled peak discharge | J-7 | J-5 | J-3 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Bonou | 2017-07-24 | 2036 m³/s | 0.012 (low) | 0.033 (low) | 0.004 (low) | missed |
| Porto-Novo | 2017-07-25 | 1853 m³/s | 0.005 (low) | 0.011 (low) | 0.004 (low) | missed |
| Adjohoun | 2017-07-24 | 2013 m³/s | 0.002 (low) | 0.014 (low) | 0.005 (low) | missed |
| Dangbo | 2017-07-24 | 2003 m³/s | 0.002 (low) | 0.029 (low) | 0.004 (low) | missed |

## Interpretation

The risk model is a signal among other evidence, not an autonomous flood
authority. The agent also considers rainfall trends and (when available) local
photo evidence. In particular, the 2017 replay is a concrete reminder that
the model can miss an event even when the simulated peak is large.

The underlying discharge is GloFAS model output, not a station measurement, and
the `crue en cours` label means the simulated discharge was already above the
zone threshold at the replay date.
