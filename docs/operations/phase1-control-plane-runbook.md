# Phase 1 Control Plane Runbook

## Purpose

Run and verify the Phase 1 control plane for VietMarket.

## Required environment

Set one of:
- `PG_URL`
- `DATABASE_URL`

The database must point at the canonical VietMarket Postgres/Timescale instance.

## Apply migrations

```bash
export PG_URL='postgres://...'
/opt/homebrew/bin/python3 packages/db/sql/apply_migrations.py
```

## Build freshness

```bash
export PG_URL='postgres://...'
/opt/homebrew/bin/python3 packages/supervisor/health/build_freshness.py
```

## Build system health

```bash
export PG_URL='postgres://...'
/opt/homebrew/bin/python3 packages/supervisor/health/build_system_health.py
```

## Full verification

```bash
export PG_URL='postgres://...'
bash scripts/verify_phase1_control_plane.sh
```

## App/API requirements

For the web app health routes to work, set one of:
- `PG_URL`
- `DATABASE_URL`

Then the following routes should return live DB-backed JSON:
- `/api/brain/health`
- `/api/brain/freshness`
- `/api/brain/workers`

The health dashboard page is:
- `/app/health`

## Known limitations in Phase 1

- Existing worker jobs are not yet universally instrumented to write `worker_runs` and `worker_failures` automatically.
- Freshness is dataset-level and timeframe-level; ticker-level freshness is deferred.
- Health is currently computed from freshness rules only, not from full Nomad job introspection.
- Recommendation and portfolio phases are intentionally absent.