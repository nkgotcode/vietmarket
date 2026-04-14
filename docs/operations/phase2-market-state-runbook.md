# Phase 2 Market State Runbook

## Purpose

Phase 2 builds deterministic market-state snapshots on top of the canonical VietMarket Timescale/Postgres store and the Phase 1 control-plane telemetry.

Outputs:
- `market_state_cycles`
- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`

The runtime is Timescale/Postgres-only, and Phase 2 consumes canonical symbol classification from `symbols`.

## Prerequisites

- Postgres reachable via `PG_URL` or `DATABASE_URL`
- Python environment with `psycopg2` available
- Canonical data tables already populated:
  - `candles`
  - `symbols`
  - `technical_indicators`
  - `fundamentals`
  - `articles`
  - `article_symbols`
  - `corporate_actions`
  - `market_stats`

## Apply migrations

```bash
export PG_URL='postgres://...'
python3 packages/db/sql/apply_migrations.py
```

Expected outcome:
- `0002_market_state.sql` applied or skipped
- `0003_symbol_classification.sql` applied or skipped

## Build prerequisite control-plane snapshots

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/health/build_freshness.py
python3 packages/supervisor/health/build_system_health.py
```

Expected outcome:
- `dataset_freshness` updated
- latest `system_health_snapshots` row available

## Sync canonical symbol classification

```bash
export PG_URL='postgres://...'
python3 packages/ingest/vn/symbol_classification_sync.py
```

Expected outcome:
- `symbols.sector_name` populated for most active tickers
- `symbols.industry_name` populated for most active tickers
- `classification_source = 'fireant'`

## Build Phase 2 market state

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/snapshots/build_market_state.py
```

Expected output shape:
- `ok: true`
- new `cycle_id`
- `ticker_snapshot_count`
- `sector_snapshot_count`
- `market_regime`
- `regime_confidence`

## Full verification

```bash
export PG_URL='postgres://...'
bash scripts/verify_phase2_market_state.sh
```

The verification script:
1. applies migrations
2. rebuilds freshness + system health
3. syncs canonical symbol classification
4. rebuilds market state
5. prints classification coverage
6. prints latest cycle
7. prints latest regime
8. prints top watchlist rows
9. prints sector breadth summary

## Manual SQL spot checks

```sql
select cycle_id, overall_status, freshness_status, frontier_status, universe_count, regime_code, created_at
from market_state_cycles
order by created_at desc
limit 5;

select ticker, sector, watchlist_score, trend_state, momentum_state
from ticker_snapshots
where cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1)
order by watchlist_score desc
limit 20;

select sector, names_count, adv_count, dec_count, breadth_pct, avg_ret_1d, avg_ret_5d
from sector_snapshots
where cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1)
order by breadth_pct desc nulls last, avg_ret_5d desc nulls last;

select market_regime, breadth_state, trend_state, liquidity_state, event_pressure_state, confidence
from market_regime_snapshots
order by created_at desc
limit 5;
```

## API surfaces

After the market-state builder has produced at least one cycle, the web app serves:
- `GET /api/brain/regime`
- `GET /api/brain/watchlist`
- `GET /api/brain/ticker/:ticker`
- `GET /api/brain/sectors`

These routes require the standard app auth flow (or the configured E2E bypass headers in test mode).

## Canonical sector and industry behavior

Phase 2 now reads true classification fields from `symbols`:
- `sector_name`
- `industry_name`
- `icb_code`
- `industry_code`
- `classification_source`

The current sync path populates these fields from FireAnt page state and stores them directly on `symbols` for canonical reuse across supervisor builds.

## Nomad automation

Periodic production refresh is defined in:
- `deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl`

Recommended workflow:
1. keep `vietmarket-symbols-sync.nomad.hcl` refreshing the symbol universe
2. run `vietmarket-symbol-classification-sync.nomad.hcl` shortly after that job
3. run the market-state builder/derived sync after classification refresh if a fully up-to-date watchlist is required

Safe validation before rollout:

```bash
nomad job plan deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl
```

Expected behavior:
- periodic batch run on `optiplex`
- reads current repo code from `/home/itsnk/vietmarket`
- updates missing classifications in Postgres without introducing any alternate runtime backend

Manual trigger:

```bash
nomad job run deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl
nomad status vietmarket-symbol-classification-sync
```


### `Missing PG_URL or DATABASE_URL`
Set one of:

```bash
export PG_URL='postgres://...'
```

## Symbol classification sync returns zero updates
Possible causes:
- FireAnt page fetches are temporarily rate-limited or blocked
- active symbol universe is empty
- `ONLY_MISSING=1` and symbols are already classified

Check:
- `select count(*) filter (where sector_name is not null), count(*) filter (where industry_name is not null) from symbols;`
- rerun with `ONLY_MISSING=0` for a full refresh

### `ticker_snapshot_count = 0`
Usually means one of:
- `symbols` is empty
- `candles` has no usable `1d` rows
- the canonical ingest pipeline is stale or blocked

Check:
- `dataset_freshness`
- latest `system_health_snapshots`
- `market_stats`

### Regime shows `risk_off` unexpectedly
Inspect:
- `system_health_snapshots.overall_status`
- `market_stats.metric = 'candles_frontier_status'`
- `market_regime_snapshots.reasoning_json`

### API routes return empty payloads
Usually no cycle has been built yet. Re-run:

```bash
python3 packages/supervisor/snapshots/build_market_state.py
```
