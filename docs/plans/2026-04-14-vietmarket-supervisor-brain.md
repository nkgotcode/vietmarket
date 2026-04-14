# VietMarket Supervisor Brain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform VietMarket from a headless ingestion platform into a production-grade Vietnam equity market intelligence and trading-supervision system, where deterministic workers populate the canonical database and Hermes operates as the top-level supervisor brain for analysis, watchlists, recommendations, paper trading, and eventual execution control.

**Architecture:** Keep the existing headless ingestion workers as the data plane. Add a control plane and intelligence plane on top of the canonical Postgres/Timescale store: explicit worker health/freshness telemetry, normalized market snapshots, signal engines, thesis/recommendation storage, portfolio/risk state, and supervisor loops that synthesize the current market state into actionable outputs. The LLM does synthesis, prioritization, contradiction detection, and explanation; deterministic services compute facts, indicators, risk limits, and execution constraints.

**Tech Stack:** Nomad, Timescale/Postgres, Python ingestion workers, Python supervisor services, Next.js web app, Hermes for reasoning/supervision, Tailscale/Telegram for operator delivery, optional broker adapters later.

---

## 0. Intent and Non-Goals

### What this system should become

VietMarket should become a three-layer production system:

1. **Data plane**
   - Headless workers ingest and normalize VN market data.
   - Workers write canonical facts into Postgres/Timescale.
   - Workers emit machine-readable run metadata, freshness, and error signals.

2. **Intelligence plane**
   - Deterministic jobs build market snapshots, indicators, event maps, and risk context.
   - Hermes reads structured market state and produces research, theses, recommendations, and operator briefings.
   - The system stores not only facts, but also judgments and decision history.

3. **Control plane**
   - Supervisor loops decide when the system is healthy enough to analyze.
   - Risk and policy gates decide what is allowed.
   - Order staging and paper trading are deterministic and auditable.

### What this system should not become in V1

- Not an unconstrained autonomous trader.
- Not a browser-first system.
- Not an LLM that infers data quality from vague logs.
- Not a system where recommendations exist only in chat memory.
- Not a system where broker execution is attempted before paper trading is stable.

### Definition of success

At any point, the operator should be able to ask:
- Is the VN market data pipeline healthy?
- What is fresh vs stale?
- What is the current market regime?
- What are the highest-conviction names and why?
- What recommendations were produced today?
- What paper positions exist, how are they performing, and why do they exist?
- What changed since the last cycle?

And the system should answer from durable state, not improvisation.

---

## 1. Current Repository State (As Inspected)

### Existing strengths

The repo already contains a meaningful base:

- `packages/ingest/vn/` for candles, gaps, symbols, repair logic, and derived sync.
- `packages/ingest/vietstock/` for discover/fetch/events/news ingestion.
- `packages/ingest/simplize/` for `fi_latest` sync.
- `deploy/nomad/jobs/` with real production-ish periodic jobs.
- `deploy/history-api/` and `apps/web/` for UI/API surfaces.
- Canonical DB already holds:
  - `candles`
  - `symbols`
  - `fi_latest`
  - `corporate_actions`
  - `financials`
  - `fundamentals`
  - `technical_indicators`
  - `indicators`
  - `market_stats`
  - `articles`
  - `article_symbols`
  - repair queue tables

### Current system shape

This is fundamentally a **data platform**, not yet a **supervisor intelligence platform**.

The repo is good at:
- pulling data headlessly
- normalizing it
- storing it
- computing some derived metrics

The repo is not yet good at:
- explicit supervisor loops
- durable recommendation history
- confidence-scored signal pipelines
- thesis memory
- portfolio state
- paper order lifecycle
- operator-grade risk control
- closed-loop decision evaluation

### Critical observed operational reality

The repo is already much easier to supervise than Hood-Legend because the workers are headless and DB-backed. That is the main architectural advantage and should be preserved.

However, the platform still has production risks:
- Nomad job health is partly inferred from child batch completion status.
- Some jobs were previously unhealthy due to placement and stale constraints.
- Some jobs still depend on network/image/runtime assumptions that are not encoded as explicit control-plane health.
- Recommendation-grade objects do not exist yet.

---

## 2. Design Principles

### Principle 1: DB-first truth

All operator-visible intelligence must be reconstructible from durable storage.

This means:
- raw worker outputs are persisted
- normalized facts are persisted
- derived state is persisted
- recommendations are persisted
- supervisor decisions are persisted
- paper trading lifecycle is persisted

Chat output is a rendering layer, never the source of truth.

### Principle 2: LLM for synthesis, not raw arithmetic truth

Deterministic code computes:
- freshness
- row counts
- indicators
- breadth
- candidate lists
- risk limits
- position sizing inputs
- execution constraints

Hermes computes:
- cross-signal synthesis
- prioritization
- thesis wording
- contradiction detection
- uncertainty framing
- watchlist curation
- trade rationale
- operator communication

### Principle 3: Fail loud, block unsafe analysis

The supervisor must refuse to generate recommendations if the data quality gate fails.

Examples:
- stale 15m candles during market hours
- symbols universe mismatch
- repair queue backlog above threshold
- articles fetch lag beyond SLA
- latest financial sync too old

### Principle 4: Recommendation history is first-class

The system must remember:
- what it believed
- what it recommended
- why it recommended it
- what invalidated it
- what happened next

Otherwise there is no learning loop.

### Principle 5: Paper trading before real trading

Before any broker automation, the system must prove that:
- signals are stable
- recommendations are coherent
- risk gates work
- supervisor decisions are auditable
- portfolio accounting is correct
- post-trade analysis is useful

### Principle 6: Separate workers from brain

Workers ingest facts.
The brain interprets facts.
The execution layer applies policy to brain outputs.
Do not collapse these roles.

---

## 3. Target Architecture

## 3.1 Layered model

### Layer A — Data Plane (existing + hardened)

Responsibilities:
- symbols sync
- candles latest
- candles gap scan
n- candles repair worker
- vietstock discover
- vietstock fetch
- corporate actions ingest
- fi_latest sync
- derived market sync

Output:
- raw and normalized tables in Postgres/Timescale
- explicit worker telemetry tables

### Layer B — Market State Plane (new)

Responsibilities:
- build ticker snapshots
- build sector snapshots
- build market regime snapshots
- compute candidate signal inputs
- maintain freshness/quality snapshots

Output:
- market-state tables suitable for Hermes consumption

### Layer C — Intelligence Plane (new)

Responsibilities:
- signal scoring
- thesis generation
- recommendation generation
- watchlist curation
- contradiction detection
- operator briefing generation

Output:
- `signal_scores`
- `theses`
- `recommendations`
- `daily_briefs`
- `supervisor_decisions`

### Layer D — Portfolio/Execution Plane (new)

Responsibilities:
- policy checks
- risk gating
- paper orders/fills/positions
- PnL and attribution
- eventual broker handoff abstraction

Output:
- `paper_orders`
- `paper_fills`
- `positions`
- `portfolio_snapshots`
- `execution_intents`
- `policy_results`

### Layer E — Interface Plane (existing + expanded)

Responsibilities:
- web dashboard
- Telegram/operator summaries
- API endpoints for market state and recommendations
- replay / audit views

---

## 4. Canonical Runtime Topology

### Runtime roles

#### Node 1: OptiPlex — primary ingestion compute
Use for:
- main Linux ingest workers
- candles latest
- discover/fetch jobs
- corporate actions
- derived sync if stable

#### Node 2: EPYC — auxiliary compute / standby / heavy jobs
Use for:
- optional standby workers
- future heavy backfills
- future training/backtesting jobs

#### Node 3: Mac mini — witness / utility / repo anchor / supervisor tooling
Use for:
- file-backed utility jobs when local assets are required
- operator-facing tools
- optional Hermes sidecar / supervisor interface
- persistent repo anchor for development and deploy scripts

#### Vultr — infra edge / public API surface
Use for:
- public history API
- external access layer
- not for supervisor truth

### Repo source-of-truth

Canonical local repo path:
- `~/Coding/vietmarket`

Remote repo counterpart currently exists at:
- `/home/itsnk/vietmarket` on the OptiPlex

Required policy:
- All architectural planning, migrations, docs, and supervisor code should converge on `~/Coding/vietmarket`.
- Deploy workflows may sync to remote runtime copies, but the human-maintained source of truth should be a clean git repo under `~/Coding/vietmarket`.

---

## 5. New Data Model (Required)

The existing tables capture market facts. We need new tables for health, judgment, and decision state.

## 5.1 Control-plane health tables

### `worker_runs`
Purpose: durable run history for every worker invocation.

Columns:
- `id`
- `job_name`
- `run_type` (`periodic`, `manual`, `replay`, `repair`)
- `nomad_job_id`
- `nomad_alloc_id`
- `node_name`
- `started_at`
- `finished_at`
- `status` (`running`, `complete`, `failed`, `partial`, `blocked`)
- `rows_read`
- `rows_written`
- `rows_upserted`
- `rows_skipped`
- `error_count`
- `warning_count`
- `summary_json`
- `created_at`

### `worker_failures`
Purpose: searchable failure ledger.

Columns:
- `id`
- `job_name`
- `run_id`
- `stage`
- `error_class`
- `error_message`
- `error_hash`
- `retryable`
- `created_at`

### `dataset_freshness`
Purpose: single place for freshness truth.

Columns:
- `dataset_name`
- `ticker`
- `tf`
- `max_event_ts`
- `max_ingested_at`
- `freshness_seconds`
- `freshness_status` (`fresh`, `lagging`, `stale`, `unknown`)
- `updated_at`

### `system_health_snapshots`
Purpose: one object per supervisor cycle saying whether the platform was healthy enough to reason.

Columns:
- `id`
- `cycle_id`
- `overall_status`
- `blocking_issues_json`
- `warnings_json`
- `worker_health_json`
- `freshness_health_json`
- `updated_at`

## 5.2 Market-state tables

### `ticker_snapshots`
One row per ticker per supervisor cycle.

Columns:
- `cycle_id`
- `ticker`
- `exchange`
- `sector`
- `price_last`
- `volume_last`
- `atr`
- `returns_1d`
- `returns_5d`
- `returns_20d`
- `trend_state`
- `momentum_state`
- `liquidity_state`
- `corporate_action_flag`
- `news_intensity`
- `financial_recency_score`
- `snapshot_json`
- `created_at`

### `sector_snapshots`
- breadth, momentum, liquidity, leadership, weakness

### `market_regime_snapshots`
- risk-on / risk-off / chop / momentum expansion / event-heavy
- breadth metrics
- frontier freshness status
- confidence

## 5.3 Intelligence tables

### `signal_scores`
One row per ticker, signal family, cycle.

Columns:
- `cycle_id`
- `ticker`
- `signal_family` (`trend`, `momentum`, `event`, `fundamental`, `liquidity`, `risk`, `relative_strength`)
- `score_raw`
- `score_normalized`
- `confidence`
- `reason_json`
- `expires_at`

### `theses`
One row per recommendation-worthy thesis.

Columns:
- `id`
- `cycle_id`
- `ticker`
- `thesis_type`
- `horizon` (`intraday`, `swing`, `position`)
- `summary`
- `supporting_evidence_json`
- `contradicting_evidence_json`
- `confidence`
- `invalidation_text`
- `invalidation_price`
- `invalidation_condition_json`
- `created_at`

### `recommendations`
One row per actionable recommendation.

Columns:
- `id`
- `cycle_id`
- `ticker`
- `side` (`long`, `short`, `avoid`, `watch`, `exit`, `trim`, `add`)
- `horizon`
- `priority`
- `confidence`
- `entry_context`
- `target_1`
- `target_2`
- `stop_condition`
- `sizing_hint`
- `thesis_id`
- `status` (`active`, `expired`, `invalidated`, `executed`, `skipped`)
- `created_at`

### `supervisor_decisions`
Purpose: durable reasoning/audit memory.

Columns:
- `id`
- `cycle_id`
- `decision_type`
- `subject_key`
- `input_packet_json`
- `decision_json`
- `model_name`
- `prompt_version`
- `created_at`

## 5.4 Portfolio/execution tables

### `paper_orders`
### `paper_fills`
### `positions`
### `portfolio_snapshots`
### `policy_results`
### `execution_intents`

These must exist before real broker execution is considered.

---

## 6. Supervisor Loop Design

## 6.1 Core cycle types

### A. Intraday micro cycle (every 5 minutes during market hours)

Purpose:
- check data health
- update snapshots for active universe
- rescore signals
- emit short-horizon recommendations and alerts

Steps:
1. Build `system_health_snapshot`
2. Abort analysis if blocking freshness/data issues exist
3. Build `ticker_snapshots`
4. Build or update `signal_scores`
5. Rank candidates
6. Generate/update `theses`
7. Generate/update `recommendations`
8. Store `supervisor_decisions`
9. Deliver operator summary if material changes occurred

### B. Catalyst cycle (every 15–30 minutes)

Purpose:
- focus on news, corporate actions, sudden state changes

Steps:
1. Read fresh `articles`, `article_symbols`, `corporate_actions`
2. Build catalyst map per ticker
3. Re-score event-driven setups
4. Generate event-specific notes and thesis updates

### C. End-of-day cycle

Purpose:
- post-market review
- next-day prep
- portfolio/post-trade learning

Steps:
1. Build day summary and breadth summary
2. Compare realized outcomes vs recommendations
3. Mark recommendation outcomes
4. Update ticker and sector notes
5. Produce next-session watchlist
6. Produce operator briefing

## 6.2 Supervisor fail-open vs fail-closed policy

Fail-closed for:
- recommendations
- trade staging
- portfolio changes

Fail-open for:
- informational reporting with explicit degraded status

Meaning:
- If candles are stale, Hermes may still say “system degraded, no recommendation permitted,”
- but it must not silently keep recommending trades.

---

## 7. Signal Engine Design

All signal families should be deterministic before Hermes sees them.

## 7.1 Required signal families

### Trend
Inputs:
- price vs SMA20/SMA50/EMA20
- multi-timeframe alignment
- slope direction

### Momentum
Inputs:
- recent returns
- breakout proximity
- relative volume
- range expansion

### Event / Catalyst
Inputs:
- corporate actions
- new article clusters
- article-symbol density
- event type severity

### Fundamental quality / value
Inputs:
- `fi_latest`
- `financials`
- `fundamentals`
- reporting recency

### Liquidity / tradability
Inputs:
- traded value
- volume persistence
- exchange
- price stability / slippage proxy

### Risk / structural warnings
Inputs:
- stale data
- weak breadth
- isolated move without confirmation
- low-liquidity anomalies
- event uncertainty

## 7.2 Output contract

Each signal family must output:
- normalized score
- confidence
- top reasons
- expiry horizon
- constraints or warnings

Hermes should consume these outputs, not recompute them from raw rows.

---

## 8. Thesis and Recommendation System

This is the core “brain” value layer.

## 8.1 Thesis types

Support at minimum:
- breakout continuation
- pullback to trend
- catalyst-driven continuation
- quality compounder watch
- liquidity trap / avoid
- regime mismatch / avoid
- mean reversion watch
- post-event digestion

## 8.2 Recommendation contract

Every recommendation must include:
- ticker
- side / action
- horizon
- confidence
- why now
- what invalidates it
- what data supported it
- what data argued against it
- whether policy allowed it

## 8.3 No orphan recommendations

A recommendation cannot exist without:
- linked cycle
- linked thesis
- linked signal evidence
- linked policy result

---

## 9. Portfolio, Risk, and Paper Trading

## 9.1 V1 policy

V1 should support:
- watchlists
- recommendations
- paper trading only
- explicit execution intents
- no direct broker action

## 9.2 Risk controls

Must include:
- max gross exposure
- max single-name exposure
- max sector exposure
- max correlated exposure
- minimum liquidity threshold
- stale-data kill switch
- event blackout rules
- daily max new positions

## 9.3 Paper trading lifecycle

1. recommendation approved by policy
2. create paper order
3. simulate fill using deterministic market rules
4. open/update position
5. track realized/unrealized PnL
6. compare realized outcome vs thesis

This produces the training/evaluation substrate before real execution.

---

## 10. APIs and Interfaces

## 10.1 Required APIs

### Health and system
- `GET /api/brain/health`
- `GET /api/brain/freshness`
- `GET /api/brain/workers`

### Market state
- `GET /api/brain/regime`
- `GET /api/brain/watchlist`
- `GET /api/brain/ticker/:ticker`
- `GET /api/brain/sectors`
- `GET /api/brain/catalysts`

### Intelligence
- `GET /api/brain/recommendations`
- `GET /api/brain/theses/:ticker`
- `GET /api/brain/daily-brief`

### Portfolio
- `GET /api/brain/portfolio`
- `GET /api/brain/orders`
- `GET /api/brain/pnl`

## 10.2 UI additions

The web app should get pages for:
- system health
- market regime
- ranked watchlist
- ticker research page
- recommendation ledger
- paper portfolio
- supervisor decision journal

---

## 11. Observability and Operations

## 11.1 Logging requirements

Every worker and supervisor job should emit structured JSON logs with:
- job_name
- run_id
- node_name
- stage
- event_type
- counts
- timings
- error_class
- message

## 11.2 Metrics requirements

Track:
- worker success rate
- worker latency
- stale dataset counts
- candidate counts per cycle
- recommendation counts per cycle
- recommendation outcome quality
- paper portfolio drawdown
- paper hit rate by thesis type

## 11.3 Alerts

Create alerts for:
- stale intraday candles during market hours
- symbols sync failure
- discover/fetch stall
- corporate actions ingest stall
- derived sync failure
- abnormal repair queue growth
- supervisor loop failure
- recommendation volume collapse or explosion

---

## 12. Security and Governance

## 12.1 Data governance

- Recommendations are advisory until execution is explicitly enabled.
- Execution intents must be separately policy-approved.
- Never let Hermes issue broker actions directly from free-form text.

## 12.2 Prompt/version governance

Store:
- prompt_version
- model_name
- supervisor input packet hash
- output hash

This is necessary for reproducibility and audit.

## 12.3 Secrets and environment

- Broker secrets must never live in prompt logs.
- DB creds should be normalized through one secrets path.
- Nomad jobs must not drift with ad hoc embedded credentials forever; migrate to variables/templates/secret injection.

---

## 13. Testing Strategy

## 13.1 Unit tests

For:
- signal scoring logic
- freshness logic
- policy gates
- position accounting
- recommendation ranking

## 13.2 Integration tests

For:
- DB pipeline from worker outputs into snapshots
- snapshot to signal generation
- signal generation to thesis creation
- thesis creation to recommendations
- recommendations to paper portfolio update

## 13.3 Replay tests

Build deterministic replay fixtures from historical DB snapshots.
Given a prior market snapshot, the supervisor should reproduce:
- the same health decision
- similar candidate ranking
- consistent policy behavior

## 13.4 Shadow evaluation

Run the supervisor in shadow mode before trusting it:
- generate recommendations without acting
- compare to subsequent market outcomes
- measure calibration and false-positive rate

---

## 14. Implementation Phases

### Phase 1 — Control Plane Hardening
Goal: make worker/platform state explicit and trustworthy.

Deliverables:
- `worker_runs`
- `worker_failures`
- `dataset_freshness`
- `system_health_snapshots`
- one unified health query / endpoint / dashboard page

### Phase 2 — Market State Layer
Goal: convert raw facts into stable market-state objects.

Deliverables:
- `ticker_snapshots`
- `sector_snapshots`
- `market_regime_snapshots`
- deterministic snapshot builder jobs

### Phase 3 — Signal Engine
Goal: create deterministic ranked signal substrate.

Deliverables:
- `signal_scores`
- signal-family computation modules
- feature importance / reason fields

### Phase 4 — Thesis and Recommendations
Goal: make Hermes useful as a true supervisor.

Deliverables:
- `theses`
- `recommendations`
- `supervisor_decisions`
- recommendation APIs
- daily/intraday briefing outputs

### Phase 5 — Paper Portfolio and Policy Engine
Goal: move from analysis platform to trading-supervision platform.

Deliverables:
- `policy_results`
- `execution_intents`
- `paper_orders`
- `paper_fills`
- `positions`
- `portfolio_snapshots`
- PnL and attribution pages

### Phase 6 — Operator Experience
Goal: make the system usable as a daily cockpit.

Deliverables:
- dashboard pages
- Telegram briefings
- watchlist views
- decision journal
- recommendation replay tools

### Phase 7 — Real Execution Readiness (later)
Only after paper trading is stable.

Deliverables:
- broker adapter abstraction
- order staging service
- broker execution policy gate
- post-trade reconciliation

---

## 15. Concrete Repository Changes

## 15.1 New directories

Create:
- `packages/supervisor/`
- `packages/supervisor/health/`
- `packages/supervisor/snapshots/`
- `packages/supervisor/signals/`
- `packages/supervisor/theses/`
- `packages/supervisor/policy/`
- `packages/supervisor/portfolio/`
- `packages/supervisor/reports/`
- `packages/db/migrations/`
- `research/tickers/`
- `research/sectors/`
- `research/daily/`
- `docs/architecture/`

## 15.2 Existing files to extend

Likely modify:
- `deploy/nomad/jobs/*.nomad.hcl`
- `packages/ingest/*`
- `apps/web/src/app/*`
- `deploy/README.md`
- `deploy/nomad/README.md`

## 15.3 New plan-adjacent docs

Create after this plan:
- `docs/architecture/supervisor-brain-overview.md`
- `docs/architecture/data-model.md`
- `docs/architecture/signal-engine.md`
- `docs/architecture/paper-trading.md`
- `docs/operations/supervisor-runbook.md`

---

## 16. Immediate Priorities From Current Reality

Based on current inspection, these should happen first before feature expansion:

1. Make job/runtime health explicit in DB instead of inferring from ad hoc logs.
2. Remove or archive obsolete ingest jobs that overlap or conflict with current discover/fetch architecture.
3. Normalize all live jobs so placement, dependencies, and success semantics are encoded consistently.
4. Add market-state and recommendation tables before adding more UI complexity.
5. Build supervisor loops only after health/freshness is first-class.

The production system will be robust only if the control plane is strong before the intelligence plane becomes ambitious.

---

## 17. Recommended End State

When complete, VietMarket should feel like this:

- Workers continuously populate canonical VN market state.
- The DB knows exactly what is healthy, stale, or degraded.
- Hermes reads a structured market packet, not raw logs.
- Hermes produces ranked, explainable recommendations.
- The system remembers all decisions and their outcomes.
- Paper portfolio management is fully auditable.
- The operator gets clean daily and intraday briefings.
- Real broker execution, if ever enabled, is downstream of deterministic policy and portfolio controls.

This is the architecture that makes Hermes the real supervisor brain — not a chat wrapper around scripts, but an operating intelligence layer on top of a robust market data platform.

---

## 18. First Implementation Epic to Execute

If starting immediately, the first production-worthy epic should be:

**Epic: Supervisor Control Plane + Market State Foundation**

Scope:
- Add health/freshness/run tables
- Add ticker/sector/regime snapshots
- Add one market-state builder job
- Add one supervisor health endpoint
- Add one operator dashboard page showing health + top snapshots

This is the minimum foundation needed before recommendation/trading logic becomes reliable.

---

Plan complete and saved to `docs/plans/2026-04-14-vietmarket-supervisor-brain.md`.
