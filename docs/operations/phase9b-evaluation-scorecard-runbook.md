# Phase 9B Evaluation Scorecard Runbook

## Purpose
Phase 9B turns Phase 7 evaluation/governance artifacts into one operator-facing scorecard.

Outputs include:
- refreshed `recommendation_outcomes`
- refreshed `replay_runs` and `replay_results`
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
- `recommendation_outcomes` contains current rows
- `replay_runs` / `replay_results` contain a fresh replay snapshot
- `calibration_metrics` contains `positive_rate`
- `/api/brain/evaluation` and `/app/evaluation` render successfully
