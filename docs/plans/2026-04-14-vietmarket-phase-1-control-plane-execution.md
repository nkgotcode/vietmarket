# VietMarket Phase 1 — Control Plane Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Phase 1 of the VietMarket supervisor-brain architecture: durable worker run/failure/freshness storage, one health builder path, one health API surface, and one operator-visible health page.

**Architecture:** Phase 1 adds a control plane on top of the current ingestion platform without rewriting the workers first. Existing jobs remain responsible for data ingestion. New shared supervisor utilities compute freshness and overall health from canonical DB tables, and new APIs/UI expose this state. The implementation should be lightweight, deterministic, DB-first, and safe to run even before later recommendation or trading phases exist.

**Tech Stack:** Postgres/Timescale, Python supervisor utilities, Next.js route handlers, React UI, Nomad-compatible CLI entrypoints.

---

## Execution Scope

### In scope
- Add migration SQL for Phase 1 control-plane tables
- Add shared supervisor Python utilities
- Add freshness builder CLI
- Add system health builder CLI
- Add DB-backed health APIs in `apps/web`
- Add one `/app/health` UI page
- Add tests for builders and route logic
- Add docs for how to run and verify Phase 1

### Out of scope
- recommendation generation
- signal engine
- paper trading
- portfolio state
- broker execution
- major refactors of ingestion business logic

---

## Task 1: Create Phase 1 migration files and schema scaffolding

**Files:**
- Create: `packages/db/migrations/0001_control_plane.sql`
- Create: `packages/db/sql/apply_migrations.py`
- Modify: `deploy/README.md`
- Test: ad hoc SQL verification via `psql`

**Steps:**
1. Write SQL migration for:
   - `worker_runs`
   - `worker_failures`
   - `dataset_freshness`
   - `system_health_snapshots`
   - `system_health_issues`
2. Add indexes on:
   - `worker_runs(job_name, started_at desc)`
   - `worker_failures(job_name, created_at desc)`
   - `dataset_freshness(dataset_name, ticker, tf)`
   - `system_health_snapshots(created_at desc)`
   - `system_health_issues(snapshot_id, severity, blocking)`
3. Add a tiny migration runner in Python that:
   - discovers `packages/db/migrations/*.sql`
   - records applied migrations in `schema_migrations`
   - applies them in lexical order
4. Document how to apply migrations.

**Verification:**
- Run migration runner against target PG_URL
- Query `information_schema.tables`
- Confirm all Phase 1 tables exist

---

## Task 2: Add shared supervisor Python foundation

**Files:**
- Create: `packages/supervisor/common/__init__.py`
- Create: `packages/supervisor/common/db.py`
- Create: `packages/supervisor/common/ids.py`
- Create: `packages/supervisor/common/logging.py`
- Create: `packages/supervisor/common/time.py`
- Create: `packages/supervisor/common/enums.py`
- Test: `tests/supervisor/common.test.mjs` or Python smoke execution

**Steps:**
1. Add `db.py`:
   - PG_URL lookup
   - connection helper
   - cursor helper
2. Add `ids.py`:
   - `new_run_id()`
   - `new_snapshot_id()`
3. Add `logging.py`:
   - JSON log emitter helper
4. Add `time.py`:
   - UTC now helpers
   - freshness interval helpers
5. Add `enums.py`:
   - run statuses
   - freshness statuses
   - health severities

**Verification:**
- Import all modules successfully with Python
- Run a one-shot script that prints generated IDs and timestamps

---

## Task 3: Add worker telemetry writers

**Files:**
- Create: `packages/supervisor/health/worker_run_writer.py`
- Create: `packages/supervisor/health/failure_writer.py`
- Create: `packages/supervisor/health/worker_summary.py`
- Modify: minimal selected workers later if needed
- Test: `tests/supervisor/worker_summary.test.mjs` or Python smoke

**Steps:**
1. Add a function to upsert/insert `worker_runs`
2. Add a function to write `worker_failures`
3. Add a helper to normalize worker summary JSON with fields like:
   - rows_written
   - warnings_count
   - errors_count
   - node_name
4. Keep these utilities independent of any specific worker for now.

**Verification:**
- Manual call inserts one synthetic worker run
- Manual failure insert creates one `worker_failures` row

---

## Task 4: Implement dataset freshness builder

**Files:**
- Create: `packages/supervisor/health/freshness_builder.py`
- Create: `packages/supervisor/health/build_freshness.py`
- Test: `tests/supervisor/freshness_builder.test.mjs` and/or Python smoke

**Steps:**
1. Define initial freshness datasets:
   - candles by tf (`15m`, `1h`, `1d`)
   - `symbols`
   - `fi_latest`
   - `corporate_actions`
   - `articles`
   - `article_symbols`
   - `financials`
   - `fundamentals`
   - `technical_indicators`
   - `indicators`
   - `market_stats`
2. For each dataset, compute:
   - max event time
   - max ingested/update time
   - freshness_seconds
   - freshness_status
3. Store results in `dataset_freshness`
4. Emit JSON summary to stdout for operational use.

**Verification:**
- Run builder successfully
- Query `dataset_freshness`
- Confirm rows exist for all tracked datasets

---

## Task 5: Implement system health builder

**Files:**
- Create: `packages/supervisor/health/system_health_builder.py`
- Create: `packages/supervisor/health/build_system_health.py`
- Test: `tests/supervisor/system_health_builder.test.mjs` and/or Python smoke

**Steps:**
1. Read `dataset_freshness`
2. Create health rules such as:
   - stale 15m candles => blocking
   - stale 1h candles => warning or blocking depending on time window
   - empty/old `fi_latest` => warning
   - old `corporate_actions` => warning
   - stale `market_stats` => warning
3. Write one row to `system_health_snapshots`
4. Write child issues into `system_health_issues`
5. Emit summary JSON:
   - snapshot_id
   - overall_status
   - blocking_issue_count
   - warning_count

**Verification:**
- Run builder
- Query latest health snapshot
- Confirm issues were recorded

---

## Task 6: Add direct DB access helper in Next.js app

**Files:**
- Create: `apps/web/src/lib/pg.ts`
- Create: `apps/web/src/lib/authz.ts`
- Modify: `apps/web/package.json`
- Test: route smoke tests + lint/build

**Steps:**
1. Add `pg` dependency to the web app
2. Create a small pooled Postgres helper using `DATABASE_URL` or `PG_URL`
3. Create shared auth helper using Clerk + E2E bypass logic
4. Keep helper narrow and server-only

**Verification:**
- Typecheck/build of web app passes
- route handlers can import helper cleanly

---

## Task 7: Implement health/freshness API routes

**Files:**
- Create: `apps/web/src/app/api/brain/health/route.ts`
- Create: `apps/web/src/app/api/brain/freshness/route.ts`
- Create: `apps/web/src/app/api/brain/workers/route.ts`
- Test: API smoke tests or local fetch tests

**Steps:**
1. `/api/brain/health`
   - return latest system snapshot + issues
2. `/api/brain/freshness`
   - return current dataset freshness rows
3. `/api/brain/workers`
   - return recent worker_runs and worker_failures
4. Protect with existing auth helper

**Verification:**
- Route handlers return 200 with real data under valid auth/bypass
- unauthorized returns 401

---

## Task 8: Implement health UI page

**Files:**
- Create: `apps/web/src/app/app/health/page.tsx`
- Create: `apps/web/src/components/health/SystemStatusBanner.tsx`
- Create: `apps/web/src/components/health/FreshnessGrid.tsx`
- Create: `apps/web/src/components/health/WorkerHealthTable.tsx`
- Optionally modify: `apps/web/src/app/app/page.tsx`
- Test: manual page smoke + optional Playwright update

**Steps:**
1. Add page that loads `/api/brain/health`, `/api/brain/freshness`, `/api/brain/workers`
2. Render:
   - overall status banner
   - list of blocking/warning issues
   - dataset freshness grid
   - recent worker runs/failures
3. Add a link from app home to `/app/health`

**Verification:**
- Page renders with real data
- no crash on empty state
- operator can see degraded/blocking issues clearly

---

## Task 9: Add lightweight tests and verification scripts

**Files:**
- Create: `tests/supervisor_phase1_smoke.test.mjs`
- Create: `scripts/verify_phase1_control_plane.sh`
- Modify: root `package.json` if useful

**Steps:**
1. Add a smoke test that checks new files/modules exist and basic command interfaces run
2. Add a shell verification script that:
   - applies migrations
   - runs freshness builder
   - runs system health builder
   - hits API endpoints if app is up
3. Make this script the standard proof for Phase 1 completion

**Verification:**
- script exits 0
- output contains tables created + rows written + endpoints returning data

---

## Task 10: Documentation and operator handoff

**Files:**
- Modify: `docs/plans/2026-04-14-vietmarket-supervisor-brain-phase-breakdown.md`
- Create: `docs/operations/phase1-control-plane-runbook.md`
- Modify: `deploy/README.md`

**Steps:**
1. Document:
   - migration command
   - freshness builder command
   - health builder command
   - expected tables
   - API routes
   - UI route
2. Record known limitations after Phase 1:
   - no recommendations yet
   - no portfolio yet
   - health mostly dataset-level, not all worker-native telemetry yet

**Verification:**
- human can follow runbook from scratch

---

## Phase 1 Completion Checklist

Phase 1 is complete only when all are true:

- [ ] Control-plane tables exist in DB
- [ ] Freshness builder writes real rows
- [ ] System health builder writes snapshots and issues
- [ ] Brain health API routes return real DB-backed JSON
- [ ] `/app/health` renders with real status
- [ ] Verification script runs successfully
- [ ] Runbook exists and is accurate

---

## Immediate Next Step After Phase 1

After Phase 1 is verified, start Phase 2 using:
- `docs/plans/2026-04-14-vietmarket-supervisor-brain-phase-breakdown.md`

The very next execution doc to create should be:
- `docs/plans/2026-04-14-vietmarket-phase-2-market-state-execution.md`

---

Plan complete and saved to `docs/plans/2026-04-14-vietmarket-phase-1-control-plane-execution.md`.
