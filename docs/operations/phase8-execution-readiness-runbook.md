# Phase 8 Execution Readiness Runbook

## Purpose
Phase 8 adds safe staging and approval rails. It does not enable autonomous live trading.

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_phase8_execution_readiness.sh
```

## API surfaces
- `GET /api/brain/execution-staging`
- `GET /api/brain/approvals`
- app page: `/app/execution`
