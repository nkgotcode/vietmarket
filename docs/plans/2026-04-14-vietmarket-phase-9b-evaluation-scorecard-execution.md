# VietMarket Phase 9B Evaluation Scorecard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a production-facing evaluation scorecard/dashboard that turns the existing Phase 7 replay, outcome, calibration, prompt, model-run, and paper-portfolio artifacts into one consumable operator surface.

**Architecture:** Reuse the existing deterministic Phase 7 scripts as the write path and add one orchestration helper for evaluation runs plus one API/page pair for read-side presentation. Keep all evaluation truth in Postgres and render the dashboard from live SQL queries; chat remains a rendering layer, never the source of truth.

**Tech Stack:** Timescale/Postgres, Python supervisor scripts, Next.js app router, TypeScript React components, shell verification scripts.

---

### Task 1: Add a deterministic evaluation-cycle runner

**Files:**
- Create: `packages/supervisor/reports/run_evaluation_cycle.py`
- Test: `tests/phase9b_evaluation_scorecard_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the runner exists.
- Assert it executes `evaluate_recommendations.py`, `run_replay.py`, and `calibration.py`.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: FAIL because the runner does not exist yet.

**Step 3: Write minimal implementation**
- Add one Python entrypoint that runs the three existing evaluation scripts in sequence.
- Capture their JSON output and print a combined JSON summary.
- Persist worker telemetry for the overall evaluation cycle.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: PASS for runner assertions.

### Task 2: Add evaluation API and page surfaces

**Files:**
- Create: `apps/web/src/app/api/brain/evaluation/route.ts`
- Create: `apps/web/src/app/app/evaluation/page.tsx`
- Create: `apps/web/src/components/evaluation/EvaluationDashboard.tsx`
- Modify: `apps/web/src/app/app/page.tsx`
- Test: `tests/phase9b_evaluation_scorecard_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the API/page/component files exist.
- Assert the API reads from `recommendation_outcomes`, `replay_runs`, `replay_results`, `calibration_metrics`, `prompt_versions`, `model_runs`, and `portfolio_snapshots`.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: FAIL because the API/page do not exist.

**Step 3: Write minimal implementation**
- API should return:
  - latest successful supervisor run
  - outcome counts and sample outcomes
  - calibration metrics
  - latest replay run and top replay rows
  - prompt registry rows
  - model runs
  - latest paper portfolio snapshot / derived equity summary
- Page should render those sections cleanly in one evaluation dashboard.
- Add a home-page link to `/app/evaluation`.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: PASS for API/page assertions.

### Task 3: Add verification docs and scripts

**Files:**
- Create: `scripts/verify_phase9b_evaluation_scorecard.sh`
- Create: `docs/operations/phase9b-evaluation-scorecard-runbook.md`
- Create: `docs/plans/2026-04-14-vietmarket-phase-9b-evaluation-scorecard-execution.md`
- Test: `tests/phase9b_evaluation_scorecard_smoke.test.mjs`

**Step 1: Write the failing test**
- Assert the verify script and runbook exist.
- Assert the verify script runs the new evaluation cycle.

**Step 2: Run test to verify it fails**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: FAIL because these files do not exist yet.

**Step 3: Write minimal implementation**
- Verification script should:
  - run the evaluation cycle
  - print outcome counts
  - print latest replay run/results
  - print calibration metrics
  - print prompt/model-run rows
- Runbook should document manual execution, verification, and dashboard surface.

**Step 4: Run test to verify it passes**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: PASS for docs/script assertions.

### Task 4: Verify B end-to-end

**Files:**
- Test: `tests/phase9b_evaluation_scorecard_smoke.test.mjs`

**Step 1: Structural verification**
Run: `node --test tests/phase9b_evaluation_scorecard_smoke.test.mjs`
Expected: PASS

**Step 2: Repo verification**
Run: `npm test`
Expected: all smoke tests pass.

**Step 3: App verification**
Run:
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`
Expected: both pass.

**Step 4: Live verification**
Run: `bash scripts/verify_phase9b_evaluation_scorecard.sh`
Expected: evaluation artifacts refreshed and queryable.
