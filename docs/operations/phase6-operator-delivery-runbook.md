# Phase 6 Operator Surfaces and Delivery Runbook

## Purpose
Phase 6 makes the supervisor operationally consumable in app and delivery surfaces.

Outputs include:
- journal views from `supervisor_decisions`
- alert summaries from policy/health state
- formatted daily brief and intraday alert payloads

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_phase6_operator_delivery.sh
```

## API surfaces
- `GET /api/brain/journal`
- `GET /api/brain/alerts`
- app pages: `/app/journal`, `/app/alerts`, `/app/system`
