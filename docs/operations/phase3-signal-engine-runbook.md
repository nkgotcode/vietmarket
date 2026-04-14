# Phase 3 Signal Engine Runbook

## Purpose

Phase 3 builds deterministic signal-family scores and ranked candidate outputs on top of the latest Phase 2 market-state cycle.

Outputs:
- `signal_scores`
- `signal_components`
- `signal_policies`
- `candidate_rankings`

The runtime is Timescale/Postgres-only. Phase 3 reads the latest completed market-state cycle and writes explainable signal rows back into canonical Postgres tables.

## Prerequisites

- Postgres reachable via `PG_URL` or `DATABASE_URL`
- Python environment with `psycopg2` available
- Phase 2 already working:
  - `market_state_cycles`
  - `ticker_snapshots`
  - `sector_snapshots`
  - `market_regime_snapshots`

## Apply migrations

```bash
export PG_URL='postgres://...'
python3 packages/db/sql/apply_migrations.py
```

Expected outcome:
- `0004_signal_engine.sql` applied or skipped

## Build Phase 2 prerequisite cycle

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/snapshots/build_market_state.py
```

Expected outcome:
- latest `market_state_cycles` row exists
- latest `ticker_snapshots` rowset exists

## Build Phase 3 signal scores

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/signals/build_signals.py
```

Expected outcome:
- family rows inserted into `signal_scores`
- explainability rows inserted into `signal_components`
- default policy row upserted into `signal_policies`

## Build candidate rankings

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/signals/rank_candidates.py
```

Expected outcome:
- `candidate_rankings` populated for the latest `cycle_id`
- rows include total score, confidence, bucket, and blocking flag

## Full verification

```bash
export PG_URL='postgres://...'
bash scripts/verify_phase3_signal_engine.sh
```

The verification script:
1. applies migrations
2. rebuilds latest market-state prerequisite cycle
3. rebuilds signal-family scores
4. rebuilds candidate rankings
5. prints family counts for the latest cycle
6. prints top ranked candidates
7. prints signal policy metadata

## Manual SQL spot checks

```sql
select signal_family, count(*)
from signal_scores
where cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1)
group by signal_family
order by signal_family;

select ticker, total_score, total_confidence, ranking_bucket, blocking_flag
from candidate_rankings
where cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1)
order by blocking_flag asc, total_score desc, total_confidence desc, ticker asc
limit 20;

select ticker, signal_family, score_raw, score_normalized, confidence, blocking_flag
from signal_scores
where cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1)
order by ticker, signal_family;
```

## API surfaces

After the signal engine has produced at least one latest-cycle output, the web app serves:
- `GET /api/brain/candidates`
- `GET /api/brain/signals`

These routes require the standard app auth flow (or the configured E2E bypass headers in test mode).

## Failure modes

### `no_market_state_cycle`
Phase 3 cannot run until Phase 2 has produced a cycle.

Run:

```bash
python3 packages/supervisor/snapshots/build_market_state.py
```

### `no_signal_scores_for_latest_cycle`
Candidate ranking was invoked before signal-family build completed.

Run:

```bash
python3 packages/supervisor/signals/build_signals.py
python3 packages/supervisor/signals/rank_candidates.py
```

### Candidate rows all look weak or blocked
Inspect:
- latest `market_regime_snapshots`
- `ticker_snapshots.health_status`
- `ticker_snapshots.liquidity_bucket`
- `signal_scores.reason_json`

### APIs return empty payloads
Usually means Phase 3 tables have not yet been populated for the latest cycle. Re-run:

```bash
python3 packages/supervisor/signals/build_signals.py
python3 packages/supervisor/signals/rank_candidates.py
```
