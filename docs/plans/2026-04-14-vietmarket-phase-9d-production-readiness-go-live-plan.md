# VietMarket Phase 9D Production Readiness and Go-Live Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Define the post-Phase-8 productionization program that takes VietMarket from a verified paper-trading supervisor stack to a disciplined proving-window operation and, later, a broker-sandbox-ready system.

**Architecture:** Treat A/B/C as the stable baseline: A supplies the daily orchestration and durable run ledger, B supplies evaluation scorecards and replay/calibration evidence, and C supplies Telegram-first operator delivery with a delivery ledger. This plan adds proving-window gates, operating rhythms, observability standards, incident/release procedures, and the broker-sandbox gate without enabling autonomous live trading.

**Tech Stack:** Timescale/Postgres, Nomad, Python supervisor services, Next.js operator app, Telegram Bot API, shell verification, future broker sandbox adapter.

---

## Current validated baseline

As of this plan:
- Daily supervisor orchestration exists and is scheduled in Nomad via `vietmarket-supervisor-daily-cycle`.
- `supervisor_runs` and `supervisor_run_steps` persist end-to-end pipeline evidence.
- Evaluation scorecards exist in app/API and refresh from `recommendation_outcomes`, `replay_runs`, `replay_results`, `calibration_metrics`, `prompt_versions`, `model_runs`, and `portfolio_snapshots`.
- Telegram operator delivery now records `delivery_events` and supports both real-send and dry-run behavior.
- Execution remains approval-gated and paper-first.

This is enough to begin a proving window. It is not yet approval to automate real broker trading.

---

## Track D1: Proving-window operations

### Objective
Run VietMarket as a stable paper-trading supervisory system for a fixed proving window before any broker-sandbox work expands.

### Required proving window
- Minimum: 20 trading sessions
- Preferred: 6 calendar weeks

### Daily acceptance checks
- `supervisor_runs.status = complete` for scheduled daily runs
- no unexpected `failed` orchestration steps
- evaluation cycle completes after daily loop
- Telegram delivery events recorded for daily brief / intraday alerts / approval queue
- operator can review recommendations, evaluation, and approvals without direct SQL

### Weekly acceptance checks
- paper equity curve available and not obviously broken by accounting drift
- recommendation volume stays within expected band
- policy rejection rate is explainable, not random
- replay rows and calibration metrics continue to refresh
- stale-data/degraded-mode events are documented and handled explicitly

---

## Track D2: Production observability and SLOs

### Goal
Turn the supervisor stack from “working” into “operationally measurable.”

### Add next
- SLO for daily cycle completion before operator deadline
- SLO for data freshness before signal generation
- SLO for Telegram delivery success rate
- alerting on:
  - daily cycle failure
  - evaluation cycle failure
  - approval queue growth
  - repeated dry-run delivery in production mode
  - stale-data gate blocking consecutive runs

### Suggested artifacts
- `docs/operations/production-slos.md`
- `scripts/check_supervisor_slos.sh`
- `/api/brain/system` expansion to include latest supervisor/evaluation/delivery status cards

---

## Track D3: Operator workflows and governance hardening

### Goal
Make the operator loop boring, explicit, and auditable.

### Next implementation tasks
- delivery-events API/page in app
- operator ack/resolve semantics for alerts
- approval action write path (approve/reject with operator identity + reason)
- approval digest grouping by urgency / stale age
- weekly review brief combining:
  - paper PnL
  - hit rate
  - replay drift
  - policy blocks
  - delivery failures

### Governance requirements
- all approval/reject actions durable in Postgres
- prompt version used for any future generative step visible in app/API
- no “hidden” execution path outside approval rails

---

## Track D4: Broker sandbox gate

### Non-negotiable rule
No real broker trading. Sandbox only, and only after proving-window criteria pass.

### Broker sandbox entry criteria
All must be true:
1. at least 20 successful trading-session runs
2. no unresolved orchestration failure pattern
3. stable paper portfolio accounting across repeated cycles
4. evaluation dashboard shows coherent positive/negative outcome distribution
5. approval workflow is durable and operator-usable from Telegram/app
6. delivery events show reliable operator notification behavior

### Sandbox scope
- map `broker_order_staging` rows into broker sandbox payloads
- write-only adapter first
- explicit human approval remains required
- reconciliation reads sandbox state back into mirror tables
- rollback path documented before first sandbox order

---

## Track D5: Release, rollback, and change-management process

### Goal
Prevent production drift and accidental behavior changes.

### Required operating rules
- every schema change ships with verification script updates
- every new supervisor step updates orchestration docs and smoke tests
- every delivery change updates `delivery_events` verification expectations
- every release candidate runs:
  - `npm test`
  - app lint/build
  - phase9 orchestration verify
  - phase9b evaluation verify
  - phase9c delivery verify
  - Nomad plan for affected jobs

### Suggested artifacts
- `docs/operations/release-checklist.md`
- `scripts/verify_productionization_bundle.sh`

---

## Recommended next execution order after this plan

1. Add delivery-events API/page + approval action write path
2. Add weekly review brief and delivery failure alerting
3. Add supervisor/delivery/evaluation SLO checks
4. Add broker sandbox adapter plan and interface contract
5. Start proving-window logging and weekly review cadence

---

## Success criteria for Phase 9D

- There is a written proving-window standard, not an implied one.
- A/B/C artifacts are treated as production operations, not demos.
- Broker sandbox work is gated by evidence, not eagerness.
- The operator has one coherent loop across app, Telegram, and DB-backed audit trails.
