# Phase 9B Evaluation Scorecard Runbook

## Purpose
Phase 9B turns Phase 7 evaluation/governance artifacts into one operator-facing scorecard.

Outputs include:
- refreshed `ticker_forward_outcomes`
- refreshed `recommendation_outcomes`
- refreshed `replay_runs` and `replay_results`
- refreshed `calibration_runs` and `calibration_buckets`
- refreshed `cohort_metrics`
- refreshed `calibration_metrics`
- prompt/model-run visibility in the app
- app page: `/app/evaluation`
- API route: `GET /api/brain/evaluation`

## Manual execution
```bash
export PG_URL='postgres://...'
python3 packages/supervisor/reports/run_evaluation_cycle.py
```

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_phase9b_evaluation_scorecard.sh
```

## Healthy result
- evaluation cycle exits 0
- `ticker_forward_outcomes` contains current rows across multiple horizons
- `recommendation_outcomes` contains current rows
- `replay_runs` / `replay_results` contain a fresh replay snapshot
- `calibration_runs` / `calibration_buckets` contain a fresh decile analysis
- `cohort_metrics` contains fresh regime and liquidity cohort rows
- `calibration_metrics` contains summary metrics such as `positive_rate_5d` and `top_bottom_spread_5d`
- `/api/brain/evaluation` and `/app/evaluation` render successfully
