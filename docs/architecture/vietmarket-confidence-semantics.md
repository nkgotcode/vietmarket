# VietMarket Confidence Semantics

## Purpose
Define what confidence means in the redesigned supervisor stack so operator UIs stop conflating evidence quality with predicted success.

## Confidence types

### Evidence confidence
Answers: "How complete and reliable are the inputs?"

Drivers:
- freshness state
- missing-feature rate
- stale fundamentals
- missing liquidity bucket
- degraded health state

### Model confidence
Answers: "How reliable has this score cohort historically been?"

Drivers:
- sample size
- score-decile hit rate
- regime-conditional performance
- calibration spread between top and bottom buckets
- stability over rolling windows

### Execution confidence
Answers: "If we acted, how likely is the implementation to be acceptable?"

Drivers:
- liquidity bucket
- turnover support
- event distortion risk
- capacity limits
- market-hours suitability

## UI rule
Never show a single naked scalar called just `confidence` once v2 recommendation objects are live.

Prefer:
- `evidence_confidence`
- `model_confidence`
- `execution_confidence`

## Legacy note
Current Phase 3 `total_confidence` should be treated as a precursor to `evidence_confidence`, not as outcome probability.
