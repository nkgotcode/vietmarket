# VietMarket Phase 5 — Portfolio, Policy, and Paper Trading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the deterministic safety, policy, and paper-trading layer that evaluates Phase 4 recommendations, stages paper orders, maintains portfolio state, and records auditable portfolio snapshots before any real execution is considered.

**Architecture:** Phase 5 reads latest-cycle recommendations, Phase 1 health state, Phase 2 market-state snapshots, and Phase 3 liquidity/risk outputs to deterministically evaluate policy compliance. Approved recommendations become execution intents and paper orders; fills and positions are simulated through a deterministic accounting path, then persisted into portfolio and PnL tables. APIs and UI read only these durable objects.

**Tech Stack:** PostgreSQL/Timescale, Python supervisor services, deterministic policy checks, Next.js App Router, authenticated server routes.

---

## Timescale/Postgres-only guardrails

- No live broker execution.
- No recommendation may become a paper order without a durable policy result.
- Portfolio state must be reconstructible from paper orders/fills/position events.
- Policy decisions must be machine-readable and stored durably for audit.

---

## Scope

### In scope
- `policy_results`
- `execution_intents`
- `paper_orders`
- `paper_fills`
- `positions`
- `portfolio_snapshots`
- `position_events`
- `risk_limits`
- deterministic policy engine
- recommendation-to-paper-order path
- portfolio/policy/order APIs and UI

### Out of scope
- real broker adapters
- actual order routing
- production cash movement

---

## Execution tasks

### Task 1: Add Phase 5 schema

**Files:**
- Create: `packages/db/migrations/0006_portfolio_policy.sql`
- Reuse: `packages/db/sql/apply_migrations.py`

**Requirements:**
- Add policy, intent, order, fill, position, portfolio snapshot, position event, and risk limit tables.
- Keep migrations idempotent.
- Add latest-cycle and portfolio-review indexes.

### Task 2: Implement policy engine

**Files:**
- Create: `packages/supervisor/policy/default_rules.py`
- Create: `packages/supervisor/policy/checks.py`
- Create: `packages/supervisor/policy/engine.py`

**Requirements:**
- Deterministically evaluate recommendations using health, freshness, liquidity, confidence, concentration, and sector rules.
- Persist machine-readable `policy_results`.
- Store blocking vs non-blocking rationale clearly.

### Task 3: Implement paper trading core

**Files:**
- Create: `packages/supervisor/portfolio/paper_order_engine.py`
- Create: `packages/supervisor/portfolio/fill_simulator.py`
- Create: `packages/supervisor/portfolio/position_book.py`
- Create: `packages/supervisor/portfolio/pnl.py`

**Requirements:**
- Convert approved recommendations into execution intents and paper orders.
- Simulate fills deterministically from current market-state price data.
- Maintain positions and position events.
- Produce durable portfolio snapshots.

### Task 4: Add portfolio reporting

**Files:**
- Create: `packages/supervisor/reports/generate_portfolio_brief.py`

**Requirements:**
- Summarize open positions, exposure, PnL, approved/blocked recommendations, and latest paper-order state.

### Task 5: Add Phase 5 APIs

**Files:**
- Create: `apps/web/src/app/api/brain/portfolio/route.ts`
- Create: `apps/web/src/app/api/brain/orders/route.ts`
- Create: `apps/web/src/app/api/brain/pnl/route.ts`
- Create: `apps/web/src/app/api/brain/policy/route.ts`

**Requirements:**
- Use `requireAppAuth`.
- Read only from Timescale/Postgres.
- Serve latest portfolio/order/policy state by default.

### Task 6: Add Phase 5 UI

**Files:**
- Create: `apps/web/src/app/app/portfolio/page.tsx`
- Create: `apps/web/src/app/app/orders/page.tsx`
- Create: `apps/web/src/components/portfolio/PortfolioSummary.tsx`
- Create: `apps/web/src/components/portfolio/PnLChart.tsx`
- Create: `apps/web/src/components/portfolio/PolicyResultPanel.tsx`
- Modify: `apps/web/src/app/app/page.tsx`

**Requirements:**
- Operators must be able to inspect approved vs blocked recommendations.
- Portfolio page should show open positions, exposure, and snapshot-level PnL.
- Orders page should show intent/order/fill lifecycle.

### Task 7: Add verification and operations docs

**Files:**
- Create: `tests/phase5_portfolio_policy_smoke.test.mjs`
- Create: `scripts/verify_phase5_portfolio_policy.sh`
- Create: `docs/operations/phase5-portfolio-policy-runbook.md`

**Verification targets:**
- root tests
- web lint
- web build
- Phase 5 smoke test
- Phase 5 DB verification script
- live DB/API run if `PG_URL` or `DATABASE_URL` is available

---

## Completion criteria

Phase 5 is complete when:
- `0006_portfolio_policy.sql` applies cleanly.
- Every latest-cycle recommendation can be evaluated into durable `policy_results`.
- Approved recommendations can produce execution intents, paper orders, fills, positions, and portfolio snapshots deterministically.
- `/api/brain/portfolio`, `/api/brain/orders`, `/api/brain/pnl`, and `/api/brain/policy` serve DB-backed outputs.
- `/app/portfolio` and `/app/orders` render auditable portfolio and order state.
- Phase 5 smoke + verification scripts pass with fresh evidence.

---

This plan follows the broader supervisor-brain roadmap and treats Phase 5 as the deterministic safety and accounting gate before any later delivery or execution-readiness work.
