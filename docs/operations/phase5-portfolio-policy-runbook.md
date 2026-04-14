# Phase 5 Portfolio, Policy, and Paper Trading Runbook

## Purpose

Phase 5 evaluates recommendations deterministically, creates durable policy results, and simulates paper orders/fills/positions before any real execution is considered.

Outputs:
- `policy_results`
- `execution_intents`
- `paper_orders`
- `paper_fills`
- `positions`
- `portfolio_snapshots`
- `position_events`
- `risk_limits`

## Prerequisites
- Postgres reachable via `PG_URL` or `DATABASE_URL`
- Phase 4 recommendations available for latest cycle

## Apply migrations
```bash
export PG_URL='postgres://...'
python3 packages/db/sql/apply_migrations.py
```

## Evaluate policy
```bash
export PG_URL='postgres://...'
python3 packages/supervisor/policy/engine.py
```

## Run deterministic paper portfolio cycle
```bash
export PG_URL='postgres://...'
python3 packages/supervisor/portfolio/paper_order_engine.py
```

## Generate portfolio brief
```bash
export PG_URL='postgres://...'
python3 packages/supervisor/reports/generate_portfolio_brief.py
```

## Full verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_phase5_portfolio_policy.sh
```

## API surfaces
- `GET /api/brain/portfolio`
- `GET /api/brain/orders`
- `GET /api/brain/pnl`
- `GET /api/brain/policy`

## Failure modes
- `no_recommendations_for_latest_cycle`: rerun Phase 4 recommendation generation
- `no_market_state_cycle`: rerun earlier phases
- empty positions: policy blocked all recommendations or no approved names met deterministic portfolio path
