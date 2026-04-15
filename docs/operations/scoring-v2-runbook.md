# Scoring V2 Runbook

## Purpose
Scoring v2 introduces explicit side-by-side scorecards for alpha, quality, risk, execution, and composite decision ranking.

## Outputs
- `score_versions`
- `alpha_scores`
- `quality_scores`
- `risk_scores_v2`
- `execution_scores`
- `decision_scores`

## Manual execution
```bash
export PG_URL='postgres://...'
python3 packages/supervisor/scoring/build_scores_v2.py
```

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_scoring_v2.sh
```

## Interpretation
- `alpha_score` estimates opportunity strength
- `quality_score` reflects input/evidence quality
- `risk_score` measures safety / downside suitability (higher is safer)
- `execution_score` measures implementation suitability
- `decision_score` is the current composite ranking score for side-by-side evaluation only
- `recommended_state` is advisory and should not re-enable paper trading by itself

## Safety note
Even with scoring v2 live, paper trading should remain disabled until promotion-policy thresholds are explicitly approved and verified.
