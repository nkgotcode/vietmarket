# VietMarket Phase 3 — Signal Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic, Timescale/Postgres-backed signal engine that turns each latest Phase 2 market-state cycle into explainable family scores and ranked candidate outputs for later thesis/recommendation generation.

**Architecture:** Phase 3 reads the latest `market_state_cycles`, `ticker_snapshots`, `sector_snapshots`, and `market_regime_snapshots` rows produced by Phase 2. Deterministic Python signal-family modules compute raw scores, normalized scores, confidence, blocking flags, and explainable components per ticker, then persist them into cycle-scoped signal tables and candidate rankings. Next.js APIs and UI pages read only these durable outputs; Hermes can consume the signal layer later without re-running ad hoc SQL.

**Tech Stack:** PostgreSQL/Timescale, Python builders with psycopg2, Next.js App Router, authenticated server routes, shell verification scripts.

---

## Timescale/Postgres-only guardrails

- Do not introduce Convex, Redis, workbook state, or any alternate signal cache.
- The signal engine must read only canonical Phase 2 tables plus existing canonical financial/article inputs if needed.
- Every signal output must be tied to one existing `cycle_id`.
- Candidate ranking must exist in durable storage before any future thesis/recommendation layer asks Hermes to narrate anything.

---

## Scope

### In scope
- `signal_scores`
- `signal_components`
- `signal_policies`
- `candidate_rankings`
- deterministic signal family modules
- candidate ranking builder
- authenticated signal/candidate APIs
- one operator-facing Phase 3 signals page
- verification script and runbook

### Out of scope
- LLM-written theses
- recommendation generation
- portfolio state
- broker execution
- policy enforcement beyond machine-readable blocking flags and ranking penalties

---

## Execution tasks

### Task 1: Add Phase 3 schema

**Files:**
- Create: `packages/db/migrations/0004_signal_engine.sql`
- Reuse: `packages/db/sql/apply_migrations.py`

**Requirements:**
- Add `signal_scores`, `signal_components`, `signal_policies`, and `candidate_rankings`.
- Use `cycle_id` as the durable join key back to Phase 2.
- Add indexes for latest-cycle reads, family breakdowns, and candidate ranking lookups.
- Keep migrations idempotent.

### Task 2: Build shared signal-engine utilities

**Files:**
- Create: `packages/supervisor/signals/__init__.py`
- Create: `packages/supervisor/signals/common.py`

**Requirements:**
- Load the latest completed Phase 2 cycle and its ticker/regime rows.
- Provide score normalization, confidence bounding, and JSON helpers shared across families.
- Centralize persistence helpers for `signal_scores`, `signal_components`, and `candidate_rankings`.

### Task 3: Implement signal families

**Files:**
- Create: `packages/supervisor/signals/trend.py`
- Create: `packages/supervisor/signals/momentum.py`
- Create: `packages/supervisor/signals/catalyst.py`
- Create: `packages/supervisor/signals/fundamentals.py`
- Create: `packages/supervisor/signals/liquidity.py`
- Create: `packages/supervisor/signals/risk.py`

**Requirements:**
- Each family returns deterministic per-ticker scores.
- Each family emits machine-readable `reason_json` plus component rows for explainability.
- Risk family should be penalty-oriented and may set blocking flags for obviously unsafe names.
- Fundamental family should prefer canonical recency/availability factors over guessed semantic mappings for opaque metric codes.

### Task 4: Build orchestrators

**Files:**
- Create: `packages/supervisor/signals/build_signals.py`
- Create: `packages/supervisor/signals/rank_candidates.py`

**Requirements:**
- `build_signals.py` should compute all family scores for the latest market-state cycle and persist them.
- `rank_candidates.py` should aggregate family outputs into ranked candidate rows for that same cycle.
- Both jobs must write Phase 1 worker-run/failure telemetry.
- Candidate rankings must include a bucket and machine-readable summary reason.

### Task 5: Add Phase 3 APIs

**Files:**
- Create: `apps/web/src/app/api/brain/signals/route.ts`
- Create: `apps/web/src/app/api/brain/candidates/route.ts`

**Requirements:**
- Use `requireAppAuth`.
- Read only from Timescale/Postgres.
- Serve latest-cycle outputs by default.
- Return stable JSON with signal family breakdowns and candidate ranking reasons.

### Task 6: Add Phase 3 UI

**Files:**
- Create: `apps/web/src/app/app/signals/page.tsx`
- Create: `apps/web/src/components/signals/SignalBreakdownTable.tsx`
- Create: `apps/web/src/components/signals/CandidateRankingTable.tsx`
- Create: `apps/web/src/components/signals/SignalsDashboard.tsx`
- Modify: `apps/web/src/app/app/page.tsx`

**Requirements:**
- Signals page must be useful without Hermes.
- Show ranked candidates first, then signal-family breakdowns.
- Surface blocking flags, confidence, and machine-readable reasons clearly.

### Task 7: Add verification and operations docs

**Files:**
- Create: `tests/phase3_signal_engine_smoke.test.mjs`
- Create: `scripts/verify_phase3_signal_engine.sh`
- Create: `docs/operations/phase3-signal-engine-runbook.md`

**Verification targets:**
- root tests
- web lint
- web build
- Phase 3 smoke test
- Phase 3 DB verification script
- optional live DB/API run if `PG_URL` or `DATABASE_URL` is available

---

## Completion criteria

Phase 3 is complete when:
- `0004_signal_engine.sql` applies cleanly through the migration runner.
- one signal-engine build writes deterministic family scores for the latest market-state cycle.
- one candidate-ranking build writes ranked outputs tied to the same `cycle_id`.
- `/api/brain/signals` and `/api/brain/candidates` serve latest-cycle Timescale/Postgres-backed signal data.
- `/app/signals` renders ranked candidates and explainable family scores.
- Phase 3 smoke + verification scripts pass with fresh evidence.

---

This plan follows the broader supervisor-brain docs and treats Phase 3 as the deterministic substrate for all later thesis, recommendation, and portfolio layers.
