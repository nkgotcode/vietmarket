# VietMarket Phase 4 — Thesis and Recommendation Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn deterministic Phase 3 signal outputs into durable, explainable theses, recommendations, and operator briefings that Hermes can generate and the web app can review outside chat.

**Architecture:** Phase 4 reads the latest `candidate_rankings`, `signal_scores`, `ticker_snapshots`, `sector_snapshots`, `market_regime_snapshots`, and Phase 1 health state to build bounded prompt packets for Hermes. Hermes must return structured JSON, which the pipeline stores both as raw output and normalized thesis/recommendation objects with explicit lifecycle state, evidence, contradictions, invalidation, and priority. Briefings are rendered as durable DB objects and served via authenticated APIs/pages.

**Tech Stack:** PostgreSQL/Timescale, Python supervisor services, Hermes structured JSON outputs, Next.js App Router, authenticated server routes.

---

## Timescale/Postgres-only guardrails

- Do not generate recommendation state only in chat memory.
- Prompt packets must be bounded and reproducible from canonical DB state.
- Hermes outputs must be stored as raw JSON plus normalized durable objects.
- Recommendations must stay read-only/operator-facing in Phase 4; no paper-order mutation path yet.

---

## Scope

### In scope
- `theses`
- `recommendations`
- `supervisor_decisions`
- `daily_briefs`
- `recommendation_outcomes`
- bounded supervisor packet builder
- structured-output parsing/normalization
- recommendation and briefing APIs/pages

### Out of scope
- policy engine
- paper orders
- portfolio state
- live or simulated execution

---

## Execution tasks

### Task 1: Add Phase 4 schema

**Files:**
- Create: `packages/db/migrations/0005_thesis_recommendation.sql`
- Reuse: `packages/db/sql/apply_migrations.py`

**Requirements:**
- Add `theses`, `recommendations`, `supervisor_decisions`, `daily_briefs`, and `recommendation_outcomes`.
- Use `cycle_id` as the durable join key back to earlier phases.
- Include raw output storage plus normalized fields.
- Add lifecycle/status indexes for latest recommendation review flows.

### Task 2: Build bounded supervisor packet assembly

**Files:**
- Create: `packages/supervisor/theses/build_supervisor_packet.py`

**Requirements:**
- Select top ranked candidates from `candidate_rankings`.
- Attach linked ticker snapshot, regime, sector, signal, and health context.
- Enforce deterministic packet size limits so Hermes inputs stay bounded and replayable.

### Task 3: Add thesis/recommendation generation pipelines

**Files:**
- Create: `packages/supervisor/theses/generate_theses.py`
- Create: `packages/supervisor/recommendations/generate_recommendations.py`
- Create: `packages/supervisor/recommendations/parse_structured_output.py`

**Requirements:**
- Hermes must return structured JSON with the agreed contract.
- Store raw output plus normalized parsed rows.
- Persist contradicting evidence, invalidation, priority, and confidence.
- Write Phase 1 worker-run/failure telemetry for every generation job.

### Task 4: Add briefing generation

**Files:**
- Create: `packages/supervisor/reports/generate_daily_brief.py`
- Create: `packages/supervisor/reports/generate_intraday_brief.py`

**Requirements:**
- Daily and intraday briefs must be durable DB objects, not transient console output.
- Briefs should summarize regime, top recommendations, blocked candidates, and changes since prior cycle.

### Task 5: Add Phase 4 APIs

**Files:**
- Create: `apps/web/src/app/api/brain/recommendations/route.ts`
- Create: `apps/web/src/app/api/brain/theses/[ticker]/route.ts`
- Create: `apps/web/src/app/api/brain/daily-brief/route.ts`

**Requirements:**
- Use `requireAppAuth`.
- Read only from Timescale/Postgres.
- Serve latest-cycle/latest-brief data by default.
- Keep payloads stable and structured for later delivery channels.

### Task 6: Add Phase 4 UI

**Files:**
- Create: `apps/web/src/app/app/recommendations/page.tsx`
- Create: `apps/web/src/app/app/briefing/page.tsx`
- Create: `apps/web/src/components/recommendations/RecommendationCard.tsx`
- Create: `apps/web/src/components/recommendations/ThesisPanel.tsx`
- Create: `apps/web/src/components/recommendations/RecommendationsDashboard.tsx`
- Modify: `apps/web/src/app/app/page.tsx`

**Requirements:**
- Operators must be able to review recommendations and theses outside chat.
- UI should expose confidence, invalidation, supporting/contradicting evidence, and status.
- Briefing page should show a durable structured summary, not only raw prose.

### Task 7: Add verification and operations docs

**Files:**
- Create: `tests/phase4_thesis_recommendation_smoke.test.mjs`
- Create: `scripts/verify_phase4_thesis_recommendation.sh`
- Create: `docs/operations/phase4-thesis-recommendation-runbook.md`

**Verification targets:**
- root tests
- web lint
- web build
- Phase 4 smoke test
- Phase 4 DB verification script
- live DB/API run if `PG_URL` or `DATABASE_URL` is available

---

## Completion criteria

Phase 4 is complete when:
- `0005_thesis_recommendation.sql` applies cleanly.
- bounded supervisor packet generation works for the latest signal cycle.
- structured Hermes outputs are stored as durable thesis/recommendation records.
- `/api/brain/recommendations`, `/api/brain/theses/[ticker]`, and `/api/brain/daily-brief` serve durable DB-backed outputs.
- `/app/recommendations` and `/app/briefing` render recommendation and briefing objects without relying on chat history.
- Phase 4 smoke + verification scripts pass with fresh evidence.

---

This plan follows the broader supervisor-brain roadmap and makes Phase 4 the durable narrative layer built on top of the deterministic Phase 3 signal substrate.
