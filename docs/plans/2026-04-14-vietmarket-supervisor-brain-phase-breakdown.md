# VietMarket Supervisor Brain — Full Phase Breakdown

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Break the VietMarket supervisor-brain architecture into a production execution program covering every phase from control-plane hardening through paper trading and eventual execution readiness.

**Architecture:** This document is the execution companion to `docs/plans/2026-04-14-vietmarket-supervisor-brain.md`. It translates the target architecture into concrete epics, services, tables, APIs, operators, files, migrations, jobs, tests, and rollout checkpoints. Every phase is independently shippable, but all phases align to one durable outcome: Hermes becomes the supervisory intelligence layer on top of a deterministic Vietnam market data platform.

**Tech Stack:** Postgres/Timescale, Nomad, Python workers/services, Next.js, Hermes, Telegram, Tailscale, optional broker adapter later.

---

## How to Use This Document

This is not a lightweight roadmap. It is the full breakdown of all phases needed for a robust production system.

Execution policy:
- Complete phases in order.
- Each phase must leave the system more robust, not just more ambitious.
- Do not start recommendation/trading features before the health/control plane is trustworthy.
- Every phase must include schema, services, APIs, UI, tests, observability, rollout, and success criteria.

Recommended implementation sequence:
1. Phase 1 — Control Plane Hardening
2. Phase 2 — Market State Layer
3. Phase 3 — Signal Engine
4. Phase 4 — Thesis + Recommendation Layer
5. Phase 5 — Portfolio + Paper Trading
6. Phase 6 — Operator Surfaces + Delivery
7. Phase 7 — Evaluation + Governance
8. Phase 8 — Execution Readiness (still not auto-live by default)

---

## Global Repository Additions

These paths will be referenced across phases.

### New top-level structure

Create:
- `packages/supervisor/`
- `packages/supervisor/common/`
- `packages/supervisor/health/`
- `packages/supervisor/snapshots/`
- `packages/supervisor/signals/`
- `packages/supervisor/theses/`
- `packages/supervisor/recommendations/`
- `packages/supervisor/policy/`
- `packages/supervisor/portfolio/`
- `packages/supervisor/reports/`
- `packages/supervisor/delivery/`
- `packages/db/migrations/`
- `packages/db/sql/`
- `docs/architecture/`
- `docs/operations/`
- `docs/apis/`
- `research/tickers/`
- `research/sectors/`
- `research/daily/`
- `tests/supervisor/`
- `tests/integration/`
- `tests/replay/`
- `tests/sql/`

### Core conventions to establish once

Add one shared convention doc:
- `docs/architecture/supervisor-conventions.md`

It should define:
- naming conventions for jobs and datasets
- run IDs and cycle IDs
- freshness status values
- signal family enum values
- thesis type enum values
- recommendation statuses
- confidence scale definition
- market-hours policy
- degraded-mode behavior

---

# Phase 1 — Control Plane Hardening

## Objective

Make worker state, freshness, and health explicit, queryable, and reliable.

This phase upgrades VietMarket from “jobs run somewhere” to “the platform knows whether it is safe to think.”

## Deliverables

- Durable worker run ledger
- Durable failure ledger
- Dataset freshness table
- System health snapshot table
- One unified health builder service/job
- One API endpoint returning current system health
- One UI page showing worker + dataset health
- Nomad job success semantics normalized enough for operator trust

## New DB objects

### Migrations

Create migration files under:
- `packages/db/migrations/0001_control_plane.sql`

Add tables:
- `worker_runs`
- `worker_failures`
- `dataset_freshness`
- `system_health_snapshots`
- `system_health_issues`

### Suggested schema scope

`worker_runs`
- run_id
- job_name
- dataset_name
- nomad_job_id
- nomad_alloc_id
- node_name
- started_at
- finished_at
- status
- rows_read
- rows_written
- rows_upserted
- warnings_count
- errors_count
- summary_json

`worker_failures`
- failure_id
- run_id
- job_name
- stage
- error_class
- error_hash
- error_message
- retryable
- created_at

`dataset_freshness`
- dataset_name
- ticker nullable
- tf nullable
- max_event_ts
- max_ingested_at
- freshness_seconds
- freshness_status
- freshness_context_json
- updated_at

`system_health_snapshots`
- snapshot_id
- cycle_id nullable
- overall_status
- data_plane_status
- freshness_status
- notes_json
- created_at

`system_health_issues`
- issue_id
- snapshot_id
- severity
- scope_type
- scope_key
- issue_code
- issue_message
- blocking
- created_at

## Code to build

### Common utilities

Create:
- `packages/supervisor/common/ids.py`
- `packages/supervisor/common/logging.py`
- `packages/supervisor/common/time.py`
- `packages/supervisor/common/db.py`
- `packages/supervisor/common/enums.py`

Responsibilities:
- deterministic run/cycle IDs
- structured JSON logging helpers
- DB connection helpers
- enum constants and validation

### Health writers

Create:
- `packages/supervisor/health/worker_run_writer.py`
- `packages/supervisor/health/failure_writer.py`
- `packages/supervisor/health/freshness_builder.py`
- `packages/supervisor/health/system_health_builder.py`

Responsibilities:
- insert/update worker runs from jobs
- compute freshness from canonical tables
- roll worker and dataset state into one system health snapshot

### Health CLI entrypoints

Create:
- `packages/supervisor/health/build_freshness.py`
- `packages/supervisor/health/build_system_health.py`

CLI behavior:
- exit 0 if system built successfully
- emit machine-readable JSON summary to stdout
- optionally fail non-zero if blocking issues are present in “strict mode”

## Existing code to modify

Modify worker scripts under:
- `packages/ingest/vn/*.py`
- `packages/ingest/vietstock/*.py`
- `packages/ingest/simplize/*.py`

Add:
- standardized start/end logging
- run ID creation
- rows_written summary output in structured JSON
- failure capture hooks

Important requirement:
Do not rewrite business logic first. Wrap existing jobs with telemetry before deeper refactors.

## Nomad changes

Add or update jobs:
- one periodic health-freshness job
- one on-demand health build job

Likely files:
- `deploy/nomad/jobs/vietmarket-system-health.nomad.hcl`
- maybe shared templates under `deploy/nomad/jobs/_common/`

## API

Create:
- `apps/web/src/app/api/brain/health/route.ts`
- `apps/web/src/app/api/brain/freshness/route.ts`
- `apps/web/src/app/api/brain/workers/route.ts`

API output should include:
- overall platform status
- worker statuses
- stale datasets
- blocking issues
- timestamps

## UI

Create:
- `apps/web/src/app/app/health/page.tsx`
- `apps/web/src/components/health/WorkerHealthTable.tsx`
- `apps/web/src/components/health/FreshnessGrid.tsx`
- `apps/web/src/components/health/SystemStatusBanner.tsx`

## Tests

### SQL tests
- migration creates all control-plane tables
- indexes and constraints correct

### Unit tests
- freshness calculation from sample candles/articles/fi data
- health severity classification
- blocking issue detection

### Integration tests
- ingest mock run → worker_runs row written
- stale dataset → health snapshot becomes degraded/blocked

### Verification commands
- migration apply command
- system health builder CLI
- API smoke test
- UI smoke test

## Success criteria

- Operator can answer “is the system healthy?” from one endpoint/page.
- Every important worker run leaves a durable run record.
- Freshness is computed from DB truth, not guessed from logs.
- Recommendation phases can safely block on health status.

---

# Phase 2 — Market State Layer

## Objective

Convert raw DB facts into stable market-state objects that Hermes can consume safely.

## Deliverables

- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`
- one snapshot builder job/service
- one market-state API surface
- one watchlist-ready state model

## New DB objects

Create migration:
- `packages/db/migrations/0002_market_state.sql`

Add tables:
- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`
- `ticker_snapshot_features`

### `ticker_snapshots`
Include:
- cycle_id
- ticker
- exchange
- sector / industry nullable at first
- price_last
- volume_last
- turnover_last
- ret_1d, ret_5d, ret_20d
- sma20_gap
- sma50_gap
- ema20_gap
- volatility_20d
- article_count_24h
- corporate_action_flag
- financial_recency_days
- liquidity_bucket
- snapshot_json
- created_at

### `sector_snapshots`
Include:
- cycle_id
- sector
- names_count
- adv_count
- dec_count
- breadth_pct
- avg_ret_1d
- avg_ret_5d
- leadership_json
- laggards_json
- created_at

### `market_regime_snapshots`
Include:
- cycle_id
- market_regime
- breadth_state
- trend_state
- liquidity_state
- event_pressure_state
- confidence
- reasoning_json
- created_at

## Code to build

Create:
- `packages/supervisor/snapshots/ticker_snapshot_builder.py`
- `packages/supervisor/snapshots/sector_snapshot_builder.py`
- `packages/supervisor/snapshots/regime_builder.py`
- `packages/supervisor/snapshots/build_market_state.py`

Responsibilities:
- read current canonical tables
- produce consistent cycle-scoped snapshot records
- store as atomic cycle output

### Suggested cycle policy

Introduce one `cycle_id` per supervisor market-state build.
That `cycle_id` should tie together:
- system health snapshot
- ticker snapshots
- sector snapshots
- regime snapshots
- later signals/recommendations

## API

Create:
- `apps/web/src/app/api/brain/regime/route.ts`
- `apps/web/src/app/api/brain/watchlist/route.ts`
- `apps/web/src/app/api/brain/ticker/[ticker]/route.ts`
- `apps/web/src/app/api/brain/sectors/route.ts`

## UI

Create:
- `apps/web/src/app/app/regime/page.tsx`
- `apps/web/src/app/app/watchlist/page.tsx`
- `apps/web/src/app/app/ticker/[ticker]/page.tsx`
- `apps/web/src/components/market/RegimeCard.tsx`
- `apps/web/src/components/market/WatchlistTable.tsx`
- `apps/web/src/components/market/TickerSnapshotCard.tsx`

## Tests

- snapshot builder with deterministic fixture DB
- sector breadth calculation tests
- regime classification tests
- API contract tests

## Success criteria

- Hermes can consume one `cycle_id` worth of structured state instead of ad hoc SQL.
- Watchlist page can render meaningful current market structure without LLM involvement.
- Regime determination is deterministic and replayable.

---

# Phase 3 — Signal Engine

## Objective

Create deterministic, confidence-scored signal families that feed Hermes.

## Deliverables

- `signal_scores`
- `signal_components`
- `signal_policies`
- signal engine services by family
- ranked candidate output per cycle

## New DB objects

Create migration:
- `packages/db/migrations/0003_signal_engine.sql`

Add tables:
- `signal_scores`
- `signal_components`
- `signal_policies`
- `candidate_rankings`

### `signal_scores`
Fields:
- cycle_id
- ticker
- signal_family
- score_raw
- score_normalized
- confidence
- horizon
- expires_at
- blocking_flag
- reason_json
- created_at

### `signal_components`
Purpose:
- store sub-factors for explainability

Fields:
- cycle_id
- ticker
- signal_family
- component_name
- component_value
- component_weight
- component_note

### `candidate_rankings`
Fields:
- cycle_id
- ticker
- total_score
- total_confidence
- ranking_bucket
- ranking_reason_json

## Signal families to implement

### Trend signals
Files:
- `packages/supervisor/signals/trend.py`

### Momentum signals
Files:
- `packages/supervisor/signals/momentum.py`

### Event/catalyst signals
Files:
- `packages/supervisor/signals/catalyst.py`

### Fundamental quality/value signals
Files:
- `packages/supervisor/signals/fundamentals.py`

### Liquidity signals
Files:
- `packages/supervisor/signals/liquidity.py`

### Risk penalty signals
Files:
- `packages/supervisor/signals/risk.py`

### Orchestrator
Files:
- `packages/supervisor/signals/build_signals.py`
- `packages/supervisor/signals/rank_candidates.py`

## API

Create:
- `apps/web/src/app/api/brain/signals/route.ts`
- `apps/web/src/app/api/brain/candidates/route.ts`

## UI

Create:
- `apps/web/src/app/app/signals/page.tsx`
- `apps/web/src/components/signals/SignalBreakdownTable.tsx`
- `apps/web/src/components/signals/CandidateRankingTable.tsx`

## Tests

- unit tests per signal family
- candidate ranking integration tests
- edge-case tests for illiquid / stale / low-confidence names

## Success criteria

- Signal outputs are deterministic and explainable.
- Candidate ranking exists before Hermes is asked to narrate anything.
- Every signal has machine-readable reasons attached.

---

# Phase 4 — Thesis and Recommendation Layer

## Objective

Turn deterministic signal outputs into durable, explainable trading and analysis hypotheses.

## Deliverables

- `theses`
- `recommendations`
- `supervisor_decisions`
- `daily_briefs`
- Hermes supervisor prompt packet builder
- intraday and EOD briefing generation

## New DB objects

Create migration:
- `packages/db/migrations/0004_thesis_recommendation.sql`

Add tables:
- `theses`
- `recommendations`
- `supervisor_decisions`
- `daily_briefs`
- `recommendation_outcomes`

## Code to build

### Prompt packet builder
- `packages/supervisor/theses/build_supervisor_packet.py`

Purpose:
- select top candidates from `candidate_rankings`
- gather linked snapshot/signal/health context
- build a bounded supervisor input packet for Hermes

### Thesis generation
- `packages/supervisor/theses/generate_theses.py`

### Recommendation generation
- `packages/supervisor/recommendations/generate_recommendations.py`

### Daily briefing
- `packages/supervisor/reports/generate_daily_brief.py`

### Intraday briefing
- `packages/supervisor/reports/generate_intraday_brief.py`

## Hermes output contract

Hermes must return structured JSON, not free text only.

Required fields:
- ticker
- thesis_type
- side
- horizon
- confidence
- why_now
- supporting_evidence
- contradicting_evidence
- invalidation
- suggested_priority
- notes

Store raw model output plus parsed normalized form.

## API

Create:
- `apps/web/src/app/api/brain/recommendations/route.ts`
- `apps/web/src/app/api/brain/theses/[ticker]/route.ts`
- `apps/web/src/app/api/brain/daily-brief/route.ts`

## UI

Create:
- `apps/web/src/app/app/recommendations/page.tsx`
- `apps/web/src/app/app/briefing/page.tsx`
- `apps/web/src/components/recommendations/RecommendationCard.tsx`
- `apps/web/src/components/recommendations/ThesisPanel.tsx`

## Tests

- supervisor packet builder bounded-size tests
- parser tests for Hermes structured output
- recommendation status lifecycle tests
- recommendation replay tests using fixtures

## Success criteria

- Recommendations are durable database objects.
- Hermes decisions are reproducible enough for audit.
- Operator can review recommendations outside chat.

---

# Phase 5 — Portfolio, Policy, and Paper Trading

## Objective

Create the deterministic safety and accounting layer required before any real execution.

## Deliverables

- risk policy engine
- paper order lifecycle
- positions and PnL tracking
- portfolio snapshotting
- recommendation-to-paper-order path

## New DB objects

Create migration:
- `packages/db/migrations/0005_portfolio_policy.sql`

Add tables:
- `policy_results`
- `execution_intents`
- `paper_orders`
- `paper_fills`
- `positions`
- `portfolio_snapshots`
- `position_events`
- `risk_limits`

## Code to build

### Policy engine
- `packages/supervisor/policy/checks.py`
- `packages/supervisor/policy/engine.py`
- `packages/supervisor/policy/default_rules.py`

Checks should include:
- system health gate
- stale data gate
- liquidity gate
- concentration gate
- sector exposure gate
- event blackout gate
- max new positions gate
- confidence floor gate

### Paper trading engine
- `packages/supervisor/portfolio/paper_order_engine.py`
- `packages/supervisor/portfolio/fill_simulator.py`
- `packages/supervisor/portfolio/position_book.py`
- `packages/supervisor/portfolio/pnl.py`

### Portfolio reporting
- `packages/supervisor/reports/generate_portfolio_brief.py`

## API

Create:
- `apps/web/src/app/api/brain/portfolio/route.ts`
- `apps/web/src/app/api/brain/orders/route.ts`
- `apps/web/src/app/api/brain/pnl/route.ts`
- `apps/web/src/app/api/brain/policy/route.ts`

## UI

Create:
- `apps/web/src/app/app/portfolio/page.tsx`
- `apps/web/src/app/app/orders/page.tsx`
- `apps/web/src/components/portfolio/PortfolioSummary.tsx`
- `apps/web/src/components/portfolio/PnLChart.tsx`
- `apps/web/src/components/portfolio/PolicyResultPanel.tsx`

## Tests

- policy gate tests per rule
- paper fill simulation tests
- position accounting tests
- PnL attribution tests
- recommendation → intent → paper order integration tests

## Success criteria

- Every recommendation can be evaluated deterministically for policy compliance.
- The system can maintain a paper portfolio with auditable state transitions.
- No recommendation can become an action without a policy result.

---

# Phase 6 — Operator Surfaces and Delivery

## Objective

Make the supervisor system operationally useful on a daily basis.

## Deliverables

- operator dashboard pages
- alert routing
- Telegram briefings
- daily recap and watchlist delivery
- decision journal views

## Code to build

### Delivery layer
- `packages/supervisor/delivery/telegram.py`
- `packages/supervisor/delivery/formatter.py`
- `packages/supervisor/delivery/dispatch_daily_brief.py`
- `packages/supervisor/delivery/dispatch_intraday_alerts.py`

### Journal layer
- `packages/supervisor/reports/generate_decision_journal.py`

## API

Create:
- `apps/web/src/app/api/brain/journal/route.ts`
- `apps/web/src/app/api/brain/alerts/route.ts`

## UI

Create pages:
- `apps/web/src/app/app/journal/page.tsx`
- `apps/web/src/app/app/alerts/page.tsx`
- `apps/web/src/app/app/watchlist/page.tsx` (enhanced)
- `apps/web/src/app/app/portfolio/page.tsx` (enhanced)
- `apps/web/src/app/app/system/page.tsx`

## Tests

- formatter tests for Telegram/daily brief payloads
- alert threshold tests
- operator dashboard smoke tests

## Success criteria

- You can consume recommendations, health, and portfolio state from the app and Telegram without manual SQL.
- Daily brief and intraday alerts are consistent and grounded in DB state.

---

# Phase 7 — Evaluation, Replay, and Governance

## Objective

Make the system measurable, auditable, and improvable.

## Deliverables

- replay harness
- recommendation outcome tracking
- calibration reporting
- prompt/version registry
- governance docs and runbooks

## New DB objects

Create migration:
- `packages/db/migrations/0006_evaluation_governance.sql`

Add tables:
- `replay_runs`
- `replay_results`
- `prompt_versions`
- `model_runs`
- `recommendation_outcomes`
- `calibration_metrics`

## Code to build

- `packages/supervisor/reports/evaluate_recommendations.py`
- `packages/supervisor/reports/run_replay.py`
- `packages/supervisor/common/prompt_registry.py`
- `packages/supervisor/reports/calibration.py`

## Docs to add

- `docs/operations/supervisor-runbook.md`
- `docs/operations/degraded-mode.md`
- `docs/operations/replay-runbook.md`
- `docs/apis/supervisor-api.md`
- `docs/architecture/data-model.md`

## Tests

- replay determinism tests
- recommendation outcome linking tests
- prompt registry tests

## Success criteria

- You can replay prior cycles and inspect what the system would have recommended.
- You can measure recommendation quality over time.
- Prompt/model decisions become auditable artifacts.

---

# Phase 8 — Execution Readiness (Optional Future Gate)

## Objective

Prepare the system for controlled real-world execution without enabling unsafe autonomy.

## Deliverables

- broker adapter abstraction
- order staging service
- post-trade reconciliation schema
- execution approval workflow

## Important rule

This phase does not mean “turn auto-trading on.”
It means “build the safe rails and approval surface so execution can be considered.”

## New code

Create:
- `packages/supervisor/execution/broker_interface.py`
- `packages/supervisor/execution/stage_order.py`
- `packages/supervisor/execution/reconcile_broker_state.py`
- `packages/supervisor/execution/approval_gate.py`

## New DB objects

Create migration:
- `packages/db/migrations/0007_execution_readiness.sql`

Add tables:
- `broker_accounts`
- `broker_order_staging`
- `broker_order_audit`
- `broker_positions_mirror`
- `execution_approvals`

## Policy requirements before any live order path

Must require:
- healthy data plane
- healthy market-state plane
- healthy policy engine
- paper trading performance thresholds met
- explicit operator approval
- auditable staging record

## Success criteria

- The system can stage a broker action safely and audibly.
- No live execution path exists without deterministic approvals.

---

# Cross-Phase Testing Matrix

Every phase should add to this matrix rather than invent ad hoc testing.

## Test categories

### 1. Schema tests
- migrations apply cleanly
- constraints correct
- rollback/reapply workable where appropriate

### 2. Unit tests
- pure calculations
- signal normalization
- policy decisions
- confidence transforms

### 3. Integration tests
- worker output → snapshot tables
- snapshot → signal scores
- scores → theses
- theses → recommendations
- recommendations → paper orders

### 4. Replay tests
- freeze a DB snapshot
- run cycle
- compare outputs

### 5. UI/API tests
- route contract tests
- page smoke tests
- operator workflow checks

### 6. Operational tests
- Nomad job can start and finish on intended node
- stale data gate actually blocks recommendations
- daily brief generation succeeds from DB state only

---

# Delivery Milestones

## Milestone A — Reliable Platform
Complete when:
- Phase 1 ships
- Phase 2 ships

## Milestone B — Reliable Analyst Brain
Complete when:
- Phase 3 ships
- Phase 4 ships

## Milestone C — Reliable Paper PM
Complete when:
- Phase 5 ships
- Phase 6 ships

## Milestone D — Governed Trading Supervisor
Complete when:
- Phase 7 ships
- Phase 8 rails exist

---

# Prioritized Implementation Order Within Phases

If resources are constrained, implement in this exact global order:

1. Phase 1 health tables and builder
2. Phase 1 health API/UI
3. Phase 2 ticker snapshots
4. Phase 2 regime snapshots
5. Phase 3 trend/momentum/liquidity signals
6. Phase 3 risk penalty signals
7. Phase 4 thesis generation
8. Phase 4 recommendation ledger
9. Phase 5 policy engine
10. Phase 5 paper portfolio
11. Phase 6 operator dashboard and daily brief
12. Phase 7 replay/evaluation
13. Phase 8 execution staging

---

# Rollout Strategy

## Rollout 1
- Deploy control plane only.
- No recommendations yet.
- Goal: trust system health.

## Rollout 2
- Deploy market-state + signal engine.
- Hermes can analyze, but recommendations remain hidden/internal.

## Rollout 3
- Turn on operator-visible recommendations.
- No paper trading yet.

## Rollout 4
- Turn on paper trading and portfolio reporting.

## Rollout 5
- Introduce replay and calibration dashboards.

## Rollout 6
- Prepare execution staging only after prior metrics are satisfactory.

---

# Concrete Next Document to Create After This One

After this document, the next working document should be:

- `docs/plans/2026-04-14-vietmarket-phase-1-control-plane-execution.md`

That document should break Phase 1 into exact file-by-file tasks, migrations, Nomad jobs, APIs, UI routes, and tests.

This current document is the full production phase map.
The next one should be the implementation ticketing plan for Phase 1.

---

# Final Guidance

If the goal is a robust production supervisor system, do not skip directly to “trade ideas” or “execution.”
The robust order is:

1. know if the platform is healthy
2. know what the market state is
3. score signals deterministically
4. synthesize theses with Hermes
5. gate recommendations by policy
6. track outcomes in paper first
7. only then discuss execution

That is how VietMarket becomes the Vietnam-equity equivalent of a serious Hood-Legend-style supervisor system instead of a pile of workers plus chat.

---

Plan complete and saved to `docs/plans/2026-04-14-vietmarket-supervisor-brain-phase-breakdown.md`.
