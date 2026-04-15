# VietMarket Scoring Trust Gaps

## Summary
The current VietMarket scoring pipeline is useful for ordering names, but not yet trustworthy enough for paper trading or operator confidence claims.

## Concrete gaps

### 1. Phase 3 score is heuristic
`candidate_rankings.total_score` is a weighted average of normalized family scores. It is not a calibrated expected-return estimate.

### 2. Confidence is overloaded
The current confidence mostly reflects evidence availability and family completeness, not probability of positive outcome.

### 3. Priority is not an independent signal
`suggested_priority` is just `100 - int(total_score)` in Phase 4 thesis generation.

### 4. Recommendation status thresholds are static
`high_conviction`, `actionable`, and `watch` are thresholded from score/confidence rather than derived from observed cohort performance.

### 5. Evaluation was too shallow
The old evaluation path reduced outcomes to sign of 5-day return, without benchmark-relative excess return, drawdown, cohort analysis, or decile calibration.

### 6. Paper trading was too tightly coupled
The daily supervisor cycle could promote heuristic recommendations straight into paper trading before a proving gate existed.

## Redesign response
The first redesign slice introduces:
- durable forward-outcome labels by horizon
- benchmark-relative excess return
- calibration runs and decile buckets
- regime/liquidity cohort metrics
- richer evaluation surfaces in the app

## Operator policy until redesign completes
- Treat legacy Phase 3 score as ranking-only.
- Do not treat confidence as trade win probability.
- Keep paper trading disabled until calibration-backed promotion policy exists.
