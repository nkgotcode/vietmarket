# Phase 4 Thesis and Recommendation Runbook

## Purpose

Phase 4 turns deterministic Phase 3 signal outputs into durable theses, recommendations, supervisor decision records, and daily brief objects.

Outputs:
- `theses`
- `recommendations`
- `supervisor_decisions`
- `daily_briefs`
- `recommendation_outcomes`

The runtime remains Timescale/Postgres-only. Phase 4 builds bounded supervisor packets from the latest cycle and stores both raw and normalized structured outputs as durable DB rows.

## Prerequisites

- Postgres reachable via `PG_URL` or `DATABASE_URL`
- Python environment with `psycopg2` available
- Phase 3 already working:
  - `signal_scores`
  - `signal_components`
  - `candidate_rankings`

## Apply migrations

```bash
export PG_URL='postgres://...'
python3 packages/db/sql/apply_migrations.py
```

Expected outcome:
- `0005_thesis_recommendation.sql` applied or skipped

## Build Phase 3 prerequisites

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/signals/build_signals.py
python3 packages/supervisor/signals/rank_candidates.py
```

Expected outcome:
- latest signal rows and candidate rankings exist

## Build bounded supervisor packet

```bash
export PG_URL='postgres://...'
python3 - <<'PY'
from packages.supervisor.common.db import connect
from packages.supervisor.theses.build_supervisor_packet import build_supervisor_packet
import json
with connect() as conn:
    print(json.dumps(build_supervisor_packet(conn), ensure_ascii=False))
PY
```

Expected outcome:
- bounded packet with latest cycle, regime, health, and top candidates

## Generate theses

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/theses/generate_theses.py
```

Expected outcome:
- `theses` populated for latest cycle
- `supervisor_decisions` records written with raw + parsed structured output

## Generate recommendations

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/recommendations/generate_recommendations.py
```

Expected outcome:
- `recommendations` populated for latest cycle
- recommendation status lifecycle rows available for operator review

## Generate daily brief

```bash
export PG_URL='postgres://...'
python3 packages/supervisor/reports/generate_daily_brief.py
python3 packages/supervisor/reports/generate_intraday_brief.py
```

Expected outcome:
- durable `daily_briefs` rows for both daily and intraday summary types

## Full verification

```bash
export PG_URL='postgres://...'
bash scripts/verify_phase4_thesis_recommendation.sh
```

The verification script:
1. applies migrations
2. rebuilds Phase 3 prerequisites
3. builds a bounded supervisor packet
4. generates theses
5. generates recommendations
6. generates the latest daily brief
7. prints latest thesis/recommendation/brief summaries

## API surfaces

After Phase 4 has produced rows, the web app serves:
- `GET /api/brain/recommendations`
- `GET /api/brain/theses/:ticker`
- `GET /api/brain/daily-brief`

These routes require standard app auth (or the E2E bypass header in test mode).

## Failure modes

### `no_market_state_cycle`
Phase 4 cannot run until earlier phases have built at least one cycle.

### `thesis_not_found`
The thesis generation job has not been run yet for the latest cycle.

Run:

```bash
python3 packages/supervisor/theses/generate_theses.py
```

### Recommendations page empty
Usually means thesis generation or recommendation generation has not run for the latest cycle.

Run:

```bash
python3 packages/supervisor/theses/generate_theses.py
python3 packages/supervisor/recommendations/generate_recommendations.py
```

### Daily brief missing
Run:

```bash
python3 packages/supervisor/reports/generate_daily_brief.py
```
