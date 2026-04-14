# VietMarket Phase 9 Productionization Sequence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the completed Phase 1–8 supervisor stack into an operator-grade production workflow by implementing A first (scheduled daily supervisor orchestration), then B (evaluation scorecards), then C (Telegram-first operator workflows), then D (post-Phase-8 productionization plan).

**Architecture:** Reuse the existing deterministic Phase 1–8 Python entrypoints as the source of truth and add a thin orchestration layer on top. Persist orchestration state in Postgres so daily runs are auditable, expose the latest run in existing operator surfaces later, and schedule the pipeline in Nomad with production-safe defaults. Treat B/C/D as follow-on layers that consume A’s durable run ledger rather than bypassing it.

**Tech Stack:** Timescale/Postgres, Python supervisor services, Nomad batch jobs, existing Next.js operator app, shell verification scripts.

---

### Task 1: Add durable orchestration schema

**Files:**
- Create: `packages/db/migrations/0009_supervisor_orchestration.sql`
- Modify: `packages/supervisor/common/ids.py`
- Test: `tests/phase9_supervisor_orchestration_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the new migration file exists.
- Assert it defines `supervisor_runs` and `supervisor_run_steps`.
- Assert `ids.py` exposes orchestration ID helpers.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: FAIL because the migration and orchestration files do not exist yet.

**Step 3: Write minimal implementation**
- Add `supervisor_runs` to persist run type, mode, status, health/cycle linkage, summary JSON, and timestamps.
- Add `supervisor_run_steps` to persist each step’s order, status, summary, and raw output.
- Add `new_supervisor_run_id()` and `new_supervisor_step_id()` helpers.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: PASS for schema/id assertions.

### Task 2: Add the daily supervisor orchestration runner

**Files:**
- Create: `packages/supervisor/orchestration/__init__.py`
- Create: `packages/supervisor/orchestration/run_supervisor_cycle.py`
- Modify: `packages/supervisor/common/ids.py`
- Test: `tests/phase9_supervisor_orchestration_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the runner file exists.
- Assert it defines a daily mode and references the expected Phase 1–6 entrypoints.
- Assert it persists into `supervisor_runs` / `supervisor_run_steps`.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: FAIL because the orchestration runner is missing.

**Step 3: Write minimal implementation**
- Build a runner that executes the existing scripts in order:
  - `packages/supervisor/health/build_freshness.py`
  - `packages/supervisor/health/build_system_health.py`
  - `packages/supervisor/snapshots/build_market_state.py`
  - `packages/supervisor/signals/build_signals.py`
  - `packages/supervisor/signals/rank_candidates.py`
  - `packages/supervisor/theses/generate_theses.py`
  - `packages/supervisor/recommendations/generate_recommendations.py`
  - `packages/supervisor/policy/engine.py`
  - `packages/supervisor/portfolio/paper_order_engine.py`
  - `packages/supervisor/reports/generate_daily_brief.py`
  - `packages/supervisor/reports/generate_decision_journal.py`
  - `packages/supervisor/delivery/dispatch_daily_brief.py`
- Capture stdout/stderr per step.
- Parse JSON summaries where available.
- Persist orchestration run + step results.
- Support `--mode daily` and a strict-health-gate flag for production scheduling.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: PASS for runner structure assertions.

### Task 3: Add Nomad scheduling for the daily supervisor cycle

**Files:**
- Create: `deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
- Test: `tests/phase9_supervisor_orchestration_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the Nomad job exists.
- Assert it schedules the new orchestration runner.
- Assert it uses `Asia/Ho_Chi_Minh` and binds the checked-out repo on OptiPlex.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: FAIL because the job file does not exist yet.

**Step 3: Write minimal implementation**
- Add a periodic batch job that runs on OptiPlex.
- Use the existing container + bind-mount pattern from `vietmarket-derived-market-sync.nomad.hcl`.
- Execute `python3 /src/packages/supervisor/orchestration/run_supervisor_cycle.py --mode daily --strict-health-gate`.
- Keep resources conservative and restart behavior fail-fast for batch semantics.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: PASS for Nomad job assertions.

### Task 4: Add verification and operator docs for A

**Files:**
- Create: `scripts/verify_phase9_supervisor_orchestration.sh`
- Create: `docs/operations/phase9-supervisor-orchestration-runbook.md`
- Modify: `docs/operations/phase6-operator-delivery-runbook.md`
- Test: `tests/phase9_supervisor_orchestration_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the verify script and runbook exist.
- Assert the runbook references the daily Nomad job and verification flow.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: FAIL because docs/scripts do not exist yet.

**Step 3: Write minimal implementation**
- Verification script should:
  - apply migrations
  - run the orchestration CLI in daily mode
  - print latest `supervisor_runs`, `supervisor_run_steps`, latest market cycle, portfolio snapshot, and daily brief rows
- Runbook should document:
  - purpose
  - job name
  - manual execution command
  - verification command
  - what success/failure looks like
  - what B/C/D build on next

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: PASS for docs/script assertions.

### Task 5: Verify A end-to-end with fresh evidence

**Files:**
- Test: `tests/phase9_supervisor_orchestration_smoke.test.mjs`
- Test: existing repo tests as needed

**Step 1: Structural verification**
Run: `node --test tests/phase9_supervisor_orchestration_smoke.test.mjs`
Expected: PASS

**Step 2: Repo verification**
Run: `npm test`
Expected: all smoke tests pass.

**Step 3: Execute the new orchestration verification**
Run: `bash scripts/verify_phase9_supervisor_orchestration.sh`
Expected: latest run recorded as complete/blocked with step rows and daily artifacts persisted.

**Step 4: Nomad validation**
Run: `nomad job plan deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
Expected: valid plan output.

### Task 6: Queue B, C, and D behind A

**Files:**
- Modify: `docs/plans/2026-04-14-vietmarket-phase-9-productionization-sequence.md`

**Step 1: Capture the post-A sequence explicitly**
- B: evaluation scorecard/dashboard grounded in `recommendation_outcomes`, replay, calibration, and paper portfolio performance.
- C: Telegram-first operator delivery and approval/ack flows grounded in A’s run ledger.
- D: post-Phase-8 productionization plan covering proving-window criteria, broker sandbox gate, and release process.

**Step 2: Use A as the dependency anchor**
- B must read latest successful `supervisor_runs`.
- C must deliver from durable artifacts created by A.
- D must reflect actual proven operational gaps after A/B/C run live.
