# VietMarket Alert System Blueprint (Fully Customizable)

## 1) Objectives

Build a production-grade alerting subsystem that is:
- **Fully customizable** (user-defined rules + logic),
- **Reliable and low-noise** (dedupe, cooldown, stateful transitions),
- **Multi-channel** (Telegram/Discord/Email/Webhook/SMS),
- **Auditable** (why fired, with payload snapshot and rule version),
- **Safe for trading ops** (critical risk + execution health alerts).

---

## 2) Design Principles

1. **Alerting is event-driven, not polling-first** where possible.
2. **Rules are data contracts**, versioned and testable.
3. **Every fire event is explainable** with condition traces.
4. **Fail closed for critical alerts** (if uncertain, escalate).
5. **Noise control is mandatory** (cooldowns, hysteresis, dedupe).

---

## 3) High-Level Architecture

```text
[Data Ingest/Derived Signals/Portfolio/Execution Events]
                |
                v
        [Event Normalizer]
                |
                v
          [Rule Engine]
      (stateful evaluator)
                |
   +------------+-------------+
   |                          |
   v                          v
[Alert State Store]      [Dispatch Router]
(history, cooldowns)      (Telegram/Discord/...)
   |                          |
   v                          v
[Audit + Replay]         [Delivery Receipts]
```

### Components
- **Event Normalizer**: converts heterogeneous events into canonical schema.
- **Rule Engine**: evaluates rules with condition graphs and time windows.
- **State Store**: per-rule/per-target state, cooldown, last-fired fingerprints.
- **Dispatch Router**: provider adapters and escalation policies.
- **Audit/Replay**: immutable fire log + replay simulator.

---

## 4) Canonical Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "price.tick|bar.close|indicator.update|news.item|portfolio.update|execution.update|system.health",
  "source": "vietmarket|broker|strategy|ops",
  "symbol": "VCB",
  "tf": "1d",
  "ts_ns": 1772460000000000000,
  "payload": {
    "close": 63.3,
    "sma20": 66.98,
    "rsi14": 44.96
  },
  "tags": ["bank", "vn30"]
}
```

Notes:
- Keep timestamps in UNIX ns for Nautilus compatibility.
- Payload is flexible but strongly typed at ingestion boundary.

---

## 5) Rule Schema (JSON/YAML)

```yaml
id: "rule_price_breakout_vcb"
name: "VCB breakout above SMA50"
enabled: true
severity: "medium" # low|medium|high|critical
scope:
  symbols: ["VCB"]
  event_types: ["bar.close"]
conditions:
  op: "AND"
  args:
    - expr: "payload.close > payload.sma50"
    - expr: "payload.volume > payload.avg_volume_20 * 1.5"
trigger:
  mode: "on_transition" # always|on_transition|once_until_reset
  reset_expr: "payload.close < payload.sma20"
noise_control:
  cooldown_sec: 1800
  hysteresis:
    enabled: true
    bands:
      enter: 0.0
      exit: -0.3
routing:
  channels: ["telegram", "discord"]
  priority: "active"
  quiet_hours:
    timezone: "Asia/Ho_Chi_Minh"
    ranges: ["23:00-07:00"]
  escalation:
    after_sec: 300
    to: ["telegram:ops", "webhook:risk"]
template:
  title: "{symbol} breakout"
  body: "Close {payload.close} > SMA50 {payload.sma50}, vol spike {payload.volume}"
metadata:
  owner: "trading"
  version: 1
```

---

## 6) Rule Engine Semantics

### Supported condition operators
- Logical: `AND`, `OR`, `NOT`
- Compare: `> >= < <= == !=`
- Set/time: `IN`, `BETWEEN`, `DURING_SESSION`
- Stateful: `crosses_above`, `crosses_below`, `changed_by_pct`

### Trigger modes
- `always`: fire every matched event (rarely used).
- `on_transition`: fire only false->true transitions.
- `once_until_reset`: fire once and wait reset condition.

### Stateful memory per rule key
Rule key = `rule_id + symbol + account(optional)`.
Stores:
- previous predicate value,
- last fire timestamp,
- last payload fingerprint,
- reset armed state.

---

## 7) Noise Control (Anti-Spam)

1. **Cooldown**: minimum time between fires.
2. **Fingerprint dedupe**: suppress duplicate payloads.
3. **Hysteresis**: separate entry/exit thresholds.
4. **Batching windows**: group related alerts every N minutes.
5. **Escalation only on non-ack** for critical alerts.

---

## 8) Routing & Delivery

### Channel adapters
- Telegram
- Discord
- Email
- SMS (optional)
- Webhook (for downstream systems)

### Delivery model
- At-least-once dispatch with idempotency key.
- Provider receipt tracking: `queued|sent|failed|ack`.
- Retry policy with exponential backoff and dead-letter queue.

### Priority policies
- `low/passive`: digest mode.
- `medium/active`: immediate push.
- `high/critical`: immediate + escalation + repeat until ack (configurable).

---

## 9) Alert Categories

### A) Market/Signal alerts
- Price breakout/breakdown
- Indicator crossovers/divergence
- Volatility spikes (ATR jump)
- Regime shifts (index/sector state)

### B) News/Catalyst alerts
- New high-impact article on watchlist symbol
- Earnings date proximity
- Corporate action changes
- Sentiment shock + novelty spikes

### C) Portfolio/Risk alerts
- Position exceeds max weight
- Daily drawdown breach
- Stop-loss/trailing-stop hit
- Beta/exposure drift

### D) Execution/Broker alerts
- Order rejected
- Partial fill stalled
- Reconcile mismatch
- Broker session disconnected

### E) Data/Ops alerts
- Stale data frontier
- Pipeline lag/backlog growth
- Job failures/restart loops
- Calendar/market-session mismatch

---

## 10) Starter Rule Pack (10 Rules)

1. `R001` Symbol breakout with volume confirmation.
2. `R002` RSI re-entry from oversold/overbought zones.
3. `R003` MACD bullish/bearish crossover on 1D.
4. `R004` ATR volatility shock (> X sigma).
5. `R005` Fresh high-severity news on portfolio symbols.
6. `R006` Earnings event in T-3, T-1, T+0 windows.
7. `R007` Position > max allocation threshold.
8. `R008` Daily realized+unrealized drawdown breach.
9. `R009` Order reject or fill-timeout.
10. `R010` Data stale (`candles_frontier_lag_ms` over threshold).

---

## 11) API Contract (Suggested)

### Rule management
- `POST /alerts/rules`
- `GET /alerts/rules`
- `GET /alerts/rules/{id}`
- `PATCH /alerts/rules/{id}`
- `DELETE /alerts/rules/{id}`
- `POST /alerts/rules/{id}/test`

### Alert operations
- `GET /alerts/fires?from=...&to=...`
- `GET /alerts/fires/{fire_id}`
- `POST /alerts/fires/{fire_id}/ack`
- `POST /alerts/replay`

### Health
- `GET /alerts/health`
- `GET /alerts/metrics`

---

## 12) Storage Model (Minimal)

### Tables
- `alert_rules`
- `alert_rule_versions`
- `alert_state`
- `alert_fires`
- `alert_dispatches`
- `alert_acks`
- `alert_dead_letters`

### Key indices
- `alert_fires(rule_id, ts_ns desc)`
- `alert_state(rule_key)` unique
- `alert_dispatches(fire_id, channel)`

---

## 13) Testing Strategy

1. **Unit tests**
   - expression parser/evaluator,
   - transition logic,
   - cooldown/hysteresis behavior.

2. **Integration tests**
   - end-to-end event -> fire -> dispatch,
   - provider failure and retry behavior.

3. **Replay tests**
   - run historical day events,
   - verify expected fire counts and timestamps.

4. **Chaos tests**
   - delayed events,
   - out-of-order events,
   - duplicate events.

---

## 14) Ops & Governance

- Rule changes are versioned and reviewable.
- Critical rules require dual approval.
- Monthly alert-noise review (top noisy rules).
- SLO target examples:
  - p95 rule evaluation latency < 200ms,
  - dispatch success > 99.5%,
  - duplicate fire rate < 0.5%.

---

## 15) Phased Delivery Plan

### Phase 1 (MVP, 1-2 weeks)
- Rule CRUD
- Basic expression engine
- Telegram + webhook dispatch
- 5 starter rules
- Audit log and simple dashboard

### Phase 2 (2-3 weeks)
- Stateful transitions + hysteresis + cooldown
- Multi-channel routing + escalation
- Replay testing + dead-letter queue

### Phase 3 (2-4 weeks)
- Portfolio/execution deep alerts
- Rule simulation UI
- Rule quality scoring and auto-suggested thresholds

---

## 16) Implementation Notes for VietMarket

- Reuse existing derived tables and market stats (e.g., `technical_indicators`, `market_stats`, `article_symbols`).
- Start with event emitters from:
  - derived sync job,
  - news ingestion job,
  - execution/reconcile modules.
- Keep broker-specific payloads behind normalized event schema.
- Integrate with OpenClaw `message` tool dispatch adapters for immediate delivery channels.


## 17) Delivered Artifacts (v1)

The following starter artifacts are now in-repo:

- Event schema: `docs/schemas/alert-event.schema.json`
- Rule schema: `docs/schemas/alert-rule.schema.json`
- Starter rules pack: `config/alerts/rules.v1.yaml`

Recommended next step:
- Implement `tools/alerts/validate_alert_rules.py` to validate `rules.v1.yaml` against `alert-rule.schema.json` in CI.

## 18) Dynamic Symbol Resolution (Watchlist + Portfolio Auto-Tracking)

To support alerts for **any ticker configured by the user** and automatically track active holdings:

### Scope selectors
Rules should use `scope.symbol_selector`:
- `static`: explicit `scope.symbols`
- `watchlist`: symbols loaded from `watchlist_id`
- `portfolio`: symbols loaded from live account positions
- `all`: no symbol restriction

### Portfolio auto-tracking
For `symbol_selector: portfolio`:
- Pull positions from broker/account sync on each portfolio update cycle.
- Maintain `portfolio_symbols_current` cache keyed by account.
- Rule engine resolves symbols at evaluation time from this cache.
- If holdings change (new symbol bought/sold out), alert coverage updates automatically.

### Data contracts (recommended)
- `watchlists(id, name, symbols[], updated_at)`
- `portfolio_snapshots(account_id, ts_ns, positions[], cash, nav)`
- `portfolio_symbols_current(account_id, symbols[], updated_at)`

### Operational behavior
- On startup, run full portfolio sync before enabling alert evaluation.
- If portfolio sync is stale, emit critical ops alert and pause `portfolio`-scoped rules.
- Keep rule runtime independent from broker adapter by consuming normalized portfolio events.

## 19) Implementation Scripts Added

- `tools/alerts/validate_alert_rules.py`
  - Validates rule YAML against schema and semantic policy checks.
- `tools/alerts/resolve_alert_scope.py`
  - Resolves symbols for each rule based on selector:
    - `static` from rule symbols,
    - `watchlist` from `config/alerts/watchlists.json`,
    - `portfolio` from `config/alerts/portfolio_symbols_current.json`,
    - `all` wildcard.

Companion config files:
- `config/alerts/watchlists.json`
- `config/alerts/portfolio_symbols_current.json`

Suggested CI steps:
```bash
python tools/alerts/validate_alert_rules.py \
  --rules config/alerts/rules.v1.yaml \
  --schema docs/schemas/alert-rule.schema.json

python tools/alerts/resolve_alert_scope.py \
  --rules config/alerts/rules.v1.yaml \
  --watchlists config/alerts/watchlists.json \
  --portfolio config/alerts/portfolio_symbols_current.json \
  --account primary
```

## 20) Alert Engine Runtime (Implemented v1)

Implemented runtime components:

- `tools/alerts/engine/expression.py`
  - Evaluates rule expressions + condition trees.
  - Supports `crosses_above` / `crosses_below` stateful operators.
- `tools/alerts/engine/state_store.py`
  - JSON-backed state store for cooldowns, transition memory, fingerprints.
- `tools/alerts/engine/dispatch.py`
  - Channel dispatch adapters (stdout adapters + webhook post).
- `tools/alerts/engine/core.py`
  - Main event processor implementing:
    - scope filtering,
    - trigger mode handling,
    - cooldown + dedupe,
    - templated messages,
    - state transitions.
- `tools/alerts/run_alert_engine.py`
  - CLI runtime entrypoint to process a normalized event file.

Supporting configs:
- `config/alerts/channels.json`
- `config/alerts/samples/event.breakout.vcb.json`

### Quick run

```bash
python tools/alerts/validate_alert_rules.py \
  --rules config/alerts/rules.v1.yaml \
  --schema docs/schemas/alert-rule.schema.json

python tools/alerts/run_alert_engine.py \
  --rules config/alerts/rules.v1.yaml \
  --watchlists config/alerts/watchlists.json \
  --portfolio config/alerts/portfolio_symbols_current.json \
  --channels config/alerts/channels.json \
  --event-file config/alerts/samples/event.breakout.vcb.json \
  --state runtime/alerts/state.json
```

## 21) Daemon + Fire Audit (Implemented)

Runtime now supports:

- **One-shot mode**: `--event-file <json>`
- **Daemon mode**: `--events-jsonl <path>` (tail-follow JSONL event stream)
- **Persistent fire audit**: appends all fired alerts to `runtime/alerts/fires.jsonl`

New helper:
- `tools/alerts/replay_firelog.py`
  - Summarizes fire history and recent events
  - Supports `--rule-id` filter

### Daemon example

```bash
python tools/alerts/run_alert_engine.py \
  --rules config/alerts/rules.v1.yaml \
  --watchlists config/alerts/watchlists.json \
  --portfolio config/alerts/portfolio_symbols_current.json \
  --channels config/alerts/channels.json \
  --events-jsonl runtime/alerts/events.jsonl \
  --state runtime/alerts/state.json \
  --firelog runtime/alerts/fires.jsonl
```

### Replay example

```bash
python tools/alerts/replay_firelog.py --firelog runtime/alerts/fires.jsonl
python tools/alerts/replay_firelog.py --firelog runtime/alerts/fires.jsonl --rule-id R001_price_breakout_volume
```

## 22) Live Event Producer (Implemented)

Added producer:
- `tools/alerts/emit_events_from_pg.py`

Purpose:
- Pull incremental events from Postgres and append normalized JSONL events for alert daemon consumption.

Current event emitters:
- `indicator.update` from `technical_indicators` delta (`asof_ts` watermark)
- `news.item` from `articles + article_symbols` (optional flag)
- `system.health` from `market_stats` (optional flag)

State file:
- `runtime/alerts/producer_state.json`

Event stream file:
- `runtime/alerts/events.jsonl`

### Producer example

```bash
python tools/alerts/emit_events_from_pg.py \
  --pg-url "$PG_URL" \
  --events-jsonl runtime/alerts/events.jsonl \
  --state runtime/alerts/producer_state.json \
  --emit-news --emit-health
```

### End-to-end daemon stack

1) Producer appends events to JSONL
2) Alert engine tails JSONL and evaluates rules
3) Fired alerts appended to firelog + dispatched

## 23) Event-Driven Daemon Mode (No Polling) — Planned Design

User requirement: **no polling**; process live data immediately when it enters the system.

### 23.1 Target architecture

```text
[Ingest / Derived jobs / Broker sync]
          |
          |  (same TX)
          +--> INSERT alert_events (durable queue)
          +--> NOTIFY alert_events, <event_id>

[Alert Daemon]
  LISTEN alert_events
     -> fetch event by id
     -> evaluate rules
     -> dispatch alerts
     -> mark processed

[Recovery path]
  On daemon startup:
    replay unprocessed rows from alert_events
```

### 23.2 Why this design
- Real-time reaction without periodic polling loops.
- Durable queue prevents event loss during daemon restarts.
- Clear at-least-once processing semantics.
- Fits current Postgres-centric architecture with minimal new infrastructure.

---

## 24) Data Model for Event-Driven Mode

### 24.1 `alert_events` table

```sql
CREATE TABLE IF NOT EXISTS alert_events (
  id                BIGSERIAL PRIMARY KEY,
  event_id          TEXT UNIQUE NOT NULL,
  event_type        TEXT NOT NULL,
  source            TEXT NOT NULL,
  symbol            TEXT NULL,
  tf                TEXT NULL,
  account_id        TEXT NULL,
  venue             TEXT NULL,
  ts_ns             BIGINT NOT NULL,
  payload           JSONB NOT NULL,
  tags              JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  processing_state  TEXT NOT NULL DEFAULT 'pending', -- pending|processing|done|error
  attempts          INT NOT NULL DEFAULT 0,
  last_error        TEXT NULL,
  processed_at      TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_events_state_created
  ON alert_events (processing_state, created_at);
```

### 24.2 `alert_daemon_offsets` (optional)

```sql
CREATE TABLE IF NOT EXISTS alert_daemon_offsets (
  daemon_name  TEXT PRIMARY KEY,
  last_event_pk BIGINT NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Use only if needed; `processing_state` model is usually sufficient.

---

## 25) Emit Path (Ingest/Derived Integration)

### 25.1 Emission contract
Every producer emits normalized events by:
1. Insert into `alert_events`
2. `NOTIFY alert_events, '<event_id>'`

Both should occur in the same transaction when possible.

### 25.2 Producers to wire
1. Derived indicator sync job -> `indicator.update`
2. News ingestion/linking job -> `news.item`
3. Health metrics update job -> `system.health`
4. Portfolio/execution sync (later) -> `portfolio.update`, `execution.update`

---

## 26) Daemon Runtime Design

### 26.1 Main loop
1. Startup replay:
   - fetch `pending/error` events (bounded batch)
   - process + mark state
2. Enter LISTEN loop:
   - wait for NOTIFY payload (`event_id`)
   - fetch event row
   - process with alert engine
   - update state to `done` or `error`

### 26.2 Reliability behaviors
- Mark row as `processing` with attempt increment.
- On crash, stale `processing` rows older than threshold return to `pending`.
- Dead-letter policy after N attempts (retain row, state=`error`).
- Idempotent processing by `event_id` + rule state store.

### 26.3 Performance targets
- p95 ingest-to-alert latency < 1s (local PG)
- Throughput target: 100+ events/sec initial
- Alert dispatch path non-blocking with bounded retry workers

---

## 27) Migration Plan from Current JSONL Producer

### Step 1
Keep current JSONL mode as fallback.

### Step 2
Add `alert_events` table and dual-write:
- existing JSONL append + new DB event insert/notify.

### Step 3
Deploy LISTEN daemon in shadow mode:
- evaluate and log only, no dispatch.

### Step 4
Switch primary runtime to LISTEN daemon.

### Step 5
Disable JSONL producer for normal operation (retain emergency fallback).

---

## 28) Security & Operational Controls

- Restrict DB role for daemon to only required tables/channels.
- Validate payload schema before insert into `alert_events`.
- Rate-limit NOTIFY flood by producer-side coalescing where needed.
- Keep full fire audit in `fires` log/table.

---

## 29) Implementation Tasks (Next)

1. Add SQL migration for `alert_events` (+ optional offsets table).
2. Add helper in producer modules to insert + notify atomically.
3. Implement `tools/alerts/run_alert_daemon.py` (LISTEN mode).
4. Implement replay/recovery and error-state transitions.
5. Add integration tests for:
   - immediate NOTIFY processing,
   - missed-notify replay,
   - crash recovery of `processing` rows,
   - idempotent duplicate event handling.


## 24) LISTEN/NOTIFY Runtime (Implemented)

Implemented files:
- `tools/alerts/sql/alert_events.sql`
- `tools/alerts/init_alert_events_table.py`
- `tools/alerts/run_alert_daemon.py`

Producer enhancement:
- `tools/alerts/emit_events_from_pg.py` now supports `--db-queue`
  - inserts into `alert_events`
  - emits `NOTIFY alert_events, <event_id>`

### Setup

```bash
python tools/alerts/init_alert_events_table.py --pg-url "$PG_URL"
```

### Start daemon (no polling loop)

```bash
python tools/alerts/run_alert_daemon.py \
  --pg-url "$PG_URL" \
  --rules config/alerts/rules.v1.yaml \
  --watchlists config/alerts/watchlists.json \
  --portfolio config/alerts/portfolio_symbols_current.json \
  --channels config/alerts/channels.json \
  --state runtime/alerts/state.json \
  --firelog runtime/alerts/fires.jsonl
```

### Emit live events into queue + notify

```bash
python tools/alerts/emit_events_from_pg.py \
  --pg-url "$PG_URL" \
  --db-queue \
  --events-jsonl runtime/alerts/events.jsonl \
  --state runtime/alerts/producer_state.json \
  --emit-news --emit-health
```

### Reliability behavior
- Daemon replays pending/error events on startup.
- Stuck `processing` rows (>5m) are reset to `pending` during replay.
- Each event tracks attempts and last_error.

## 25) Ops Hardening + Real Channel Delivery (Implemented)

### 25.1 Daemon operations scripts

Added:
- `tools/alerts/daemon_ctl.sh`
  - `start|stop|restart|status|logs`
  - manages PID + log files under `runtime/alerts/`
- `tools/alerts/daemon_health.py`
  - checks queue health (`pending`, `error`, `stuck_processing`)
  - exits non-zero when unhealthy

### 25.2 Real channel delivery adapters

`tools/alerts/engine/dispatch.py` now supports:
- Telegram Bot API (`sendMessage`)
- Discord webhook
- Generic webhook
- dead-letter JSONL on failed sends

Config file:
- `config/alerts/channels.json`

Optional env overrides:
- `ALERT_TELEGRAM_BOT_TOKEN`
- `ALERT_TELEGRAM_CHAT_ID`
- `ALERT_DISCORD_WEBHOOK_URL`
- `ALERT_WEBHOOK_URL`

### 25.3 Quick ops commands

```bash
# start daemon
PG_URL="$PG_URL" tools/alerts/daemon_ctl.sh start

# health check
python tools/alerts/daemon_health.py --pg-url "$PG_URL"

# view logs
tools/alerts/daemon_ctl.sh logs
```

## 26) Service Templates + Dead-Letter Replay (Implemented)

### Added files
- `deploy/alerts/alert-daemon.systemd.service`
- `deploy/nomad/jobs/vietmarket-alert-daemon.nomad.hcl`
- `tools/alerts/replay_dead_letters.py`

### Dead-letter replay usage

```bash
# replay last 100 dead letters
python tools/alerts/replay_dead_letters.py \
  --dead-letter runtime/alerts/dead_letters.jsonl \
  --channels config/alerts/channels.json \
  --limit 100

# replay only telegram and truncate after attempt
python tools/alerts/replay_dead_letters.py \
  --channel telegram \
  --truncate
```

### Suggested ops routine
1. Keep daemon running under systemd or Nomad template.
2. Run `daemon_health.py` from monitoring every 1-5 minutes.
3. Replay dead letters periodically (or on demand) after fixing channel credentials.
