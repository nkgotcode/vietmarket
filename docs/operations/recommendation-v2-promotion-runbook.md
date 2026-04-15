# Recommendation V2 Promotion Runbook

## Purpose
This runbook documents the recommendation layer after the switch to scoring v2 decision states.

## What changed
- recommendations are now generated from `decision_scores`
- recommendation status maps to explicit promotion states such as `paper_eligible`, `candidate`, `watch`, and `research_only`
- recommendation payloads include alpha/quality/risk/execution/decision metrics and confidence types
- intraday and daily brief generation prefer v2 decision semantics

## Verification targets
- `packages/supervisor/recommendations/generate_recommendations.py`
- `apps/web/src/app/api/brain/recommendations/route.ts`
- `apps/web/src/components/recommendations/*`
- `packages/supervisor/reports/generate_daily_brief.py`
- `packages/supervisor/reports/generate_intraday_brief.py`
- `packages/supervisor/policy/engine.py`

## Safety note
Paper trading remains disabled. `paper_eligible` is currently advisory semantics for evaluation and review only.
