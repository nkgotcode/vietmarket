# VietMarket Phase 2 — Market State Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Timescale/Postgres-only market-state layer that turns canonical VietMarket data plus Phase 1 control-plane telemetry into deterministic cycle-scoped ticker, sector, and regime snapshots for Hermes supervision.

**Architecture:** Phase 2 reads only canonical Timescale/Postgres tables plus Phase 1 dataset freshness and system-health outputs. Each build creates one `cycle_id`, writes normalized ticker/sector/regime snapshots for that cycle, and exposes them through authenticated Next.js APIs and pages. Canonical symbol classification is stored directly on `symbols`, and market-state snapshots consume those fields instead of any exchange-derived fallback grouping.

**Tech Stack:** PostgreSQL/Timescale, Python snapshot builders with psycopg2, Next.js App Router, authenticated server routes, shell verification scripts.

---

## Timescale/Postgres-only guardrails

- Do not add any new alternate cache/backend dependency or fallback path.
- Canonical reads must come from Timescale/Postgres tables already used by the runtime:
  - `candles`
  - `symbols`
  - `technical_indicators`
  - `indicators`
  - `financials`
  - `fundamentals`
  - `fi_latest`
  - `corporate_actions`
  - `articles`
  - `article_symbols`
  - `market_stats`
  - `dataset_freshness`
  - `system_health_snapshots`
  - `system_health_issues`
- `symbols.sector_name`, `symbols.industry_name`, `symbols.icb_code`, `symbols.industry_code`
- Keep market-state grouping on true sector/industry metadata from canonical symbol classification, not exchange-based placeholders.

---

## Scope

### In scope
- `market_state_cycles`
- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`
- one deterministic market-state cycle builder
- authenticated market-state APIs
- watchlist / regime / ticker-state UI pages
- Phase 2 verification script and runbook
- legacy runtime cleanup in active app + ingest paths

### Out of scope
- LLM recommendations
- signal family scoring tables
- paper trading
- broker execution
- historical backfill of every prior market-state cycle

---

## Execution tasks

### Task 1: Rewrite schema around market-state cycles

**Files:**
- Create: `packages/db/migrations/0002_market_state.sql`
- Reuse: `packages/db/sql/apply_migrations.py`

**Deliverables:**
- `market_state_cycles`
- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`
- indexes for latest-cycle and ticker lookup flows

**Requirements:**
- `cycle_id` is the durable join key for all Phase 2 snapshot tables.
- Tables must be idempotent under reruns of the migration script.
- Schema must support deterministic rebuilds without mutating prior completed cycles.

### Task 2: Build deterministic snapshot utilities

**Files:**
- Create: `packages/supervisor/snapshots/common.py`
- Create: `packages/supervisor/snapshots/ticker_snapshot_builder.py`
- Create: `packages/supervisor/snapshots/sector_snapshot_builder.py`
- Create: `packages/supervisor/snapshots/regime_builder.py`
- Create: `packages/supervisor/snapshots/build_market_state.py`
- Modify: `packages/supervisor/common/ids.py`

**Builder responsibilities:**
- Load the latest control-plane health + freshness context.
- Create one new `cycle_id`.
- Build ticker rows from canonical candles / indicators / articles / corporate actions / financial recency and canonical symbol classification.
- Build sector aggregates from ticker snapshots using true sector metadata.
- Build one regime row from ticker breadth, trend, liquidity, event pressure, and frontier freshness.
- Record the cycle summary in `market_state_cycles`.
- Record a worker run and failure entry using the Phase 1 control-plane writers.

**Cycle policy:**
- One build = one `cycle_id`.
- `market_state_cycles` is append-only.
- Phase 2 may attach the latest health snapshot to the cycle, but it must never rely on non-canonical state.

### Task 3: Define Phase 2 snapshot semantics

**Ticker snapshot fields:**
- `ticker`, `exchange`, `sector`
- `price_last`, `volume_last`, `turnover_last`
- `ret_1d`, `ret_5d`, `ret_20d`
- `sma20_gap`, `sma50_gap`, `ema20_gap`
- `volatility_20d`
- `article_count_24h`
- `corporate_action_flag`
- `financial_recency_days`
- `liquidity_bucket`
- `trend_state`, `momentum_state`
- `watchlist_score`
- `health_status`
- `snapshot_json`

**Sector snapshot fields:**
- `sector`
- `names_count`, `adv_count`, `dec_count`
- `breadth_pct`
- `avg_ret_1d`, `avg_ret_5d`
- `leadership_json`, `laggards_json`
- `snapshot_json`

**Regime snapshot fields:**
- `market_regime`
- `breadth_state`
- `trend_state`
- `liquidity_state`
- `event_pressure_state`
- `confidence`
- `watchlist_count`
- `reasoning_json`

### Task 4: Add authenticated market-state APIs

**Files:**
- Create: `apps/web/src/app/api/brain/regime/route.ts`
- Create: `apps/web/src/app/api/brain/watchlist/route.ts`
- Create: `apps/web/src/app/api/brain/ticker/[ticker]/route.ts`
- Create: `apps/web/src/app/api/brain/sectors/route.ts`

**Requirements:**
- Use `requireAppAuth`.
- Read only from Timescale/Postgres via `getPgPool()`.
- Serve latest cycle by default.
- Return stable JSON payloads that are easy for later Hermes consumption.

### Task 5: Add Phase 2 pages and components

**Files:**
- Create: `apps/web/src/app/app/regime/page.tsx`
- Create: `apps/web/src/app/app/watchlist/page.tsx`
- Create: `apps/web/src/app/app/ticker-state/[ticker]/page.tsx`
- Create supporting components under `apps/web/src/components/market/`
- Modify: `apps/web/src/app/app/page.tsx`

**Requirements:**
- Pages must be useful without LLM involvement.
- Regime page should show current regime plus breadth/liquidity/event context.
- Watchlist page should rank actionable tickers from the latest cycle.
- Ticker-state page should expose one ticker’s deterministic market-state packet.

### Task 6: Remove legacy runtime paths

**Files / paths:**
- Remove the deleted legacy app/backend paths and obsolete job specs that are no longer part of the Timescale/Postgres runtime.
- Modify: `apps/web/package.json`
- Modify: `apps/web/package-lock.json`
- Modify: `apps/web/tsconfig.json`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/app/app/chart-demo/page.tsx`
- Modify: `apps/web/scripts/smoke.mjs`
- Modify: `packages/ingest/vn/candles_batch_run.sh`
- Modify: `packages/ingest/vn/candles_backfill.py`

**Requirements:**
- No active web build path depends on the removed legacy backend.
- No active candle ingest path writes outside the canonical Timescale/Postgres flow.
- Remove outdated historical references from active docs/comments/tests where appropriate.

### Task 7: Add canonical symbol classification

**Files:**
- Create: `packages/db/migrations/0003_symbol_classification.sql`
- Create: `packages/ingest/vn/symbol_classification_sync.py`
- Modify: `packages/supervisor/snapshots/ticker_snapshot_builder.py`
- Modify: `packages/supervisor/snapshots/sector_snapshot_builder.py`
- Modify: `packages/supervisor/snapshots/regime_builder.py`
- Modify: `scripts/verify_phase2_market_state.sh`
- Modify: `docs/operations/phase2-market-state-runbook.md`

**Requirements:**
- Persist `sector_name`, `industry_name`, `icb_code`, `industry_code`, and classification provenance on `symbols`.
- Populate classification from a reproducible upstream source.
- Rebuild sector and regime snapshots from true classification metadata.

### Task 8: Add verification and operations docs

**Files:**
- Create: `tests/phase2_market_state_smoke.test.mjs`
- Create: `scripts/verify_phase2_market_state.sh`
- Create: `docs/operations/phase2-market-state-runbook.md`

**Verification targets:**
- root tests
- web lint
- web build
- Phase 2 smoke test
- Phase 2 DB verification script
- optional live DB run if `PG_URL` or `DATABASE_URL` is available

### Task 9: Automate canonical classification refresh and expose classification codes cleanly

**Files:**
- Create: `deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl`
- Modify: `docs/operations/phase2-market-state-runbook.md`
- Modify: `apps/web/src/app/api/brain/watchlist/route.ts`
- Modify: `apps/web/src/app/api/brain/ticker/[ticker]/route.ts`
- Modify: `apps/web/src/components/market/WatchlistTable.tsx`
- Modify: `apps/web/src/components/market/TickerSnapshotCard.tsx`
- Modify: `apps/web/src/components/market/TickerStateDashboard.tsx`
- Modify: `apps/web/src/components/market/WatchlistDashboard.tsx`

**Requirements:**
- Add a periodic Nomad batch job that runs `packages/ingest/vn/symbol_classification_sync.py` on the production runner without introducing any non-Postgres dependency.
- Schedule the job after the symbol-universe sync so new tickers can be classified automatically.
- Keep the API response stable while exposing `industry_name`, `icb_code`, `industry_code`, and `classification_source` as explicit fields instead of forcing UI consumers to parse them only from `snapshot_json`.
- Show the classification codes directly in ticker and watchlist UI surfaces so operators can validate market-state provenance without opening raw JSON.

---

## Completion criteria

Phase 2 is complete when:
- `0002_market_state.sql` applies cleanly through the migration runner.
- One market-state build writes a new `cycle_id` plus ticker / sector / regime outputs.
- `/api/brain/regime`, `/api/brain/watchlist`, `/api/brain/ticker/[ticker]`, and `/api/brain/sectors` serve latest-cycle Timescale/Postgres-backed data.
- A periodic Nomad job keeps canonical symbol classification refreshed from the approved upstream source.
- Watchlist and ticker-state API/UI surfaces expose `industry_name`, `icb_code`, and `industry_code` explicitly alongside sector names.
- `/app/regime`, `/app/watchlist`, and `/app/ticker-state/[ticker]` render meaningful data.
- `apps/web` no longer depends on the removed legacy backend to lint or build.
- `candles_batch_run.sh` and `candles_backfill.py` are Timescale/Postgres-only in active execution flow.
- Phase 2 smoke + verification scripts pass with fresh evidence.

---

This plan reflects the Timescale/Postgres-only Phase 2 architecture with canonical symbol classification feeding sector and regime snapshots.
