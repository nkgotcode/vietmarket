# SmartOne Web Trading Automation — Full Implementation Plan

## 1) Goals & Operating Principles

### Primary goals
1. Automate market-time lifecycle (start/stop safely).
2. Automate signal generation + portfolio management.
3. Execute spot orders with strict risk controls.
4. Minimize LLM code-generation during live trading.

### Principles
- **Deterministic scripts first, LLM second**.
- **Human-confirm mode by default**, then optional full-auto.
- **Fail closed**: if anything uncertain, no order.
- **Every action auditable**.

---

## 2) High-Level Architecture

### Services
1. **Market Clock Service**
   - Knows trading days, holidays, pre-open, session, lunch break, close.
   - Emits state: `CLOSED | PREOPEN | OPEN_MORNING | BREAK | OPEN_AFTERNOON | POSTCLOSE`.

2. **Data Service (VietMarket adapter)**
   - Pulls candles, fundamentals, indicators, news.
   - Normalizes to local schema/cache for strategy engine.

3. **Strategy Engine**
   - Reads normalized data.
   - Produces signals + target weights + risk tags.
   - Outputs deterministic **Order Intents** (not raw browser actions).

4. **Risk Engine**
   - Validates intents: max position, turnover, slippage guard, drawdown caps, symbol allowlist.

5. **Execution Engine (SmartOne Web Adapter)**
   - Browser automation for login/session/order placement.
   - Idempotent order submission + status reconciliation.

6. **Orchestrator**
   - Starts/stops loops based on Market Clock.
   - Handles retries, health checks, emergency stop.

7. **Ops & Audit**
   - Logs, metrics, alerts, replayable event journal.

---

## 3) Repo Layout (Low-Context Reliability)

```bash
trading-automation/
  config/
    trading.yaml
    risk.yaml
    broker_smartone.yaml
    market_calendar.yaml
  scripts/
    bootstrap_env.sh
    run_clock.py
    run_data_sync.py
    run_signals.py
    run_rebalance.py
    run_execution.py
    reconcile_orders.py
    healthcheck.py
    kill_switch.py
  src/
    clock/
      market_calendar.py
      trading_sessions.py
    data/
      vietmarket_client.py
      cache_store.py
      schemas.py
    strategy/
      factor_rules.py
      portfolio_builder.py
      signal_pipeline.py
    risk/
      pretrade_checks.py
      intraday_limits.py
    execution/
      smartone_browser.py
      order_router.py
      order_state_machine.py
    ops/
      event_log.py
      notifier.py
      state_store.py
  tests/
    unit/
    integration/
    paper/
  fixtures/
    historical_days/
    broker_ui_snapshots/
  docs/
    runbook.md
    incident_playbook.md
```

---

## 4) Market Open/Close Automation Plan

### 4.1 Time logic (Asia/Ho_Chi_Minh)
- Use exchange timezone hard-coded + IANA zone.
- Maintain local holiday file (`market_calendar.yaml`) + optional sync source.
- Session windows for VN equities:
  - Pre-open
  - Morning open
  - Midday break
  - Afternoon open
  - Post-close

### 4.2 Clock behavior
- Every 30s/60s compute market state.
- Publish state to `state_store` + event log.
- Orchestrator reacts:
  - `PREOPEN`: warm sessions, sync data, dry-run checks.
  - `OPEN_*`: enable signal + execution loops.
  - `BREAK`: pause new entries, allow reconciliation only.
  - `POSTCLOSE`: disable execution, run EOD reconciliation/report.

### 4.3 Safety
- If holiday/calendar uncertainty: mark `CLOSED` and notify.
- Manual override flag (`force_open=false` default).

---

## 5) SmartOne Execution Implementation (Phased)

### Phase A — Read-only automation
- Login/session check.
- Pull portfolio, cash, open orders, fills.
- No order placement.
- Validate selectors + resilience to UI changes.

### Phase B — Paper execution mode
- Strategy produces Order Intents.
- Risk checks run.
- Execution adapter simulates submit and records intended actions.

### Phase C — Human-confirm live
- Generate orders automatically.
- Send summary (qty/price/risk impact).
- Require explicit confirm before submit.

### Phase D — Limited full-auto
- Small-capital sandbox.
- Strict symbol allowlist.
- Daily max notional + max loss + max orders.
- Kill switch tested weekly.

---

## 6) Helper Scripts to Avoid On-the-Fly LLM Coding

### Must-have scripts
1. `scripts/run_clock.py`  
   Deterministic market state transitions.

2. `scripts/run_data_sync.py`  
   Pull VietMarket snapshot into local cache.

3. `scripts/run_signals.py`  
   Build signals from fixed strategy templates.

4. `scripts/run_rebalance.py`  
   Convert targets to Order Intents.

5. `scripts/run_execution.py`  
   Submit/modify/cancel through broker adapter.

6. `scripts/reconcile_orders.py`  
   Compare intent vs broker result; heal mismatches.

7. `scripts/healthcheck.py`  
   One-shot full system diagnostic.

8. `scripts/kill_switch.py`  
   Hard stop all new orders + cancel pending (policy-based).

### Utility modules
- `price_rounding.py` (tick-size normalization)
- `position_sizer.py` (risk-based sizing)
- `idempotency.py` (client order IDs)
- `retry_policy.py` (exponential backoff, bounded)
- `selector_registry.py` (UI selector versions)

---

## 7) Strategy & Risk Baseline

### Strategy v1
- Universe: allowlist of liquid symbols.
- Entry conditions: trend + momentum + liquidity + news sanity.
- Exit conditions: stop-loss, trailing stop, trend breakdown, max hold.
- Rebalance cadence: fixed interval during open sessions.

### Risk v1 hard rules
- Max % NAV per symbol.
- Max total exposure.
- Max daily turnover.
- Max daily drawdown (hard stop).
- No trade if:
  - stale data,
  - clock not OPEN session,
  - broker session unhealthy,
  - spread/slippage over threshold.

---

## 8) Testing & Validation Plan

### 8.1 Unit tests
- Calendar/session transitions.
- Indicator/signal logic.
- Risk checks.
- Price/tick rounding.

### 8.2 Integration tests
- VietMarket adapter against live/staging data.
- SmartOne read-only flows.
- End-to-end paper mode.

### 8.3 Replay/backtest-lite
- Replay historical day snapshots to verify:
  - order intent stability,
  - risk gate behavior,
  - no out-of-session orders.

### 8.4 Shadow run
- Run full stack for 1–2 weeks without live orders.
- Compare simulated actions vs expected behavior.

---

## 9) Scheduling & Operations

- Clock: always-on lightweight loop.
- Data sync: fixed interval in market hours, slower off-hours.
- Signals/rebalance: open-session only.
- Reconcile: periodic + EOD.
- Daily reports: post-close.

Add alerting for:
- missed clock ticks,
- stale data,
- login failures,
- rejected orders,
- risk-trip events.

---

## 10) Security & Compliance

- Secrets in vault/env only (never in prompts).
- Dedicated trading machine/session profile.
- Session recording + immutable audit logs.
- Respect broker terms and exchange rules.
- Manual emergency stop always available.

---

## 11) Delivery Roadmap

### Week 1
- Repo scaffolding + market clock + data adapter + healthchecks.

### Week 2
- Strategy v1 + risk engine + paper-mode order intent flow.

### Week 3
- SmartOne read-only + confirm-mode submit flow + reconciliation.

### Week 4
- Shadow run + hardening + limited-capital live pilot.

---

## 12) Nautilus Adapter Contract (SmartOne Bridge)

This section defines a stable boundary between NautilusTrader and the SmartOne web execution adapter, following Nautilus principles of:
- ports/adapters,
- event-driven order lifecycle,
- reconciliation as a first-class operation.

### 12.1 Integration intent

Use Nautilus as the **core execution/risk/portfolio engine** and keep SmartOne as an external adapter.

- Nautilus side: strategy commands, risk checks, portfolio state.
- SmartOne adapter side: submit/modify/cancel/query via web automation.
- Bridge contract: deterministic DTOs (`OrderIntent`, `BrokerAck`, `FillEvent`, `ReconcileResult`).

### 12.2 Canonical enums

```python
from enum import Enum

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"

class IntentStatus(str, Enum):
    CREATED = "CREATED"
    SENT = "SENT"
    ACKED = "ACKED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
```

### 12.3 `OrderIntent` (Nautilus -> SmartOne Adapter)

```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class OrderIntent:
    # identity / idempotency
    client_order_id: str               # globally unique; generated by Nautilus side
    strategy_id: str                   # Nautilus strategy identifier
    account_id: str                    # broker account
    venue: str                         # e.g. "VPS_SMARTONE"
    symbol: str                        # exchange-native symbol (e.g. VCB)

    # order semantics
    side: Side
    order_type: OrderType
    quantity: Decimal
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    tif: TimeInForce = TimeInForce.DAY
    reduce_only: bool = False
    post_only: bool = False

    # safeguards
    max_slippage_bps: Optional[int] = None
    risk_tag: Optional[str] = None
    kill_switch_armed: bool = True

    # timing
    created_at_ns: int = 0             # UNIX ns, aligned with Nautilus convention
    expires_at_ns: Optional[int] = None

    # metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Validation rules:
- `quantity > 0`
- `limit_price` required for `LIMIT`/`STOP_LIMIT`
- `stop_price` required for `STOP`/`STOP_LIMIT`
- symbol must pass allowlist + market session checks
- reject if `created_at_ns` is stale beyond policy

### 12.4 `BrokerAck` (SmartOne Adapter -> Nautilus)

```python
@dataclass(frozen=True)
class BrokerAck:
    client_order_id: str
    broker_order_id: Optional[str]     # may be absent on hard reject
    account_id: str
    venue: str

    accepted: bool
    status: IntentStatus               # ACKED or REJECTED
    reason_code: Optional[str] = None  # normalized internal reason code
    reason_text: Optional[str] = None  # raw broker/UI reason

    acknowledged_at_ns: int = 0
    raw_payload: Optional[dict] = None
```

Reason code normalization (examples):
- `REJECT_INVALID_PRICE_TICK`
- `REJECT_INSUFFICIENT_BUYING_POWER`
- `REJECT_SESSION_CLOSED`
- `REJECT_DUPLICATE_CLIENT_ORDER_ID`
- `REJECT_BROKER_VALIDATION`
- `ERROR_AUTOMATION_TIMEOUT`

### 12.5 `FillEvent` (SmartOne Adapter -> Nautilus)

```python
@dataclass(frozen=True)
class FillEvent:
    client_order_id: str
    broker_order_id: str
    trade_id: str

    account_id: str
    venue: str
    symbol: str
    side: Side

    fill_qty: Decimal
    fill_price: Decimal
    commission: Decimal = Decimal("0")
    commission_ccy: Optional[str] = None

    liquidity_flag: Optional[str] = None  # MAKER/TAKER/UNKNOWN
    event_at_ns: int = 0                  # broker event time if available
    received_at_ns: int = 0               # adapter ingestion time

    cumulative_qty: Optional[Decimal] = None
    leaves_qty: Optional[Decimal] = None
    order_status: Optional[IntentStatus] = None

    raw_payload: Optional[dict] = None
```

Behavior:
- Emit one `FillEvent` per execution.
- Enforce dedup key: `(broker_order_id, trade_id)`.
- Update cumulative order state after each fill.

### 12.6 `ReconcileResult` (periodic + startup reconciliation)

```python
@dataclass(frozen=True)
class ReconcileResult:
    run_id: str
    account_id: str
    venue: str
    started_at_ns: int
    finished_at_ns: int

    # order state reconciliation
    missing_locally: int                # broker has, local missing
    missing_broker: int                 # local open, broker missing
    status_mismatches: int
    fill_mismatches: int

    # position and cash reconciliation
    position_mismatches: int
    cash_mismatches: int

    # actions applied by reconciler
    synthetic_acks_emitted: int
    synthetic_fills_emitted: int
    stale_orders_closed: int

    ok: bool
    notes: list[str]
```

Reconciliation policy:
- Run at startup, every N minutes in-session, and post-close.
- If mismatch above thresholds -> trip risk gate (`execution_degraded=true`), stop new intents.

### 12.7 Adapter interface (port) for SmartOne

```python
from typing import Protocol, Sequence

class SmartOneExecutionPort(Protocol):
    def submit_order(self, intent: OrderIntent) -> BrokerAck: ...
    def modify_order(self, client_order_id: str, *, new_qty=None, new_limit_price=None, new_stop_price=None) -> BrokerAck: ...
    def cancel_order(self, client_order_id: str) -> BrokerAck: ...

    def fetch_open_orders(self, account_id: str) -> Sequence[dict]: ...
    def fetch_order_history(self, account_id: str, since_ns: int) -> Sequence[dict]: ...
    def fetch_fills(self, account_id: str, since_ns: int) -> Sequence[dict]: ...
    def fetch_positions(self, account_id: str) -> Sequence[dict]: ...
    def fetch_cash(self, account_id: str) -> dict: ...

    def reconcile(self, account_id: str, since_ns: int) -> ReconcileResult: ...
```

Implementation note:
- Keep the browser-specific logic behind this port (`smartone_browser.py`), never leak selectors into strategy/risk code.

### 12.8 Nautilus mapping (command/event bridge)

- Nautilus strategy emits trading command -> converted to `OrderIntent`.
- RiskEngine approves -> adapter `submit_order()`.
- `BrokerAck` mapped to Nautilus order-accepted/rejected event.
- `FillEvent` mapped to Nautilus fill/execution report event.
- `ReconcileResult` drives synthetic events + risk circuit-breaker.

### 12.9 State machine (required)

Order lifecycle (minimum):

`CREATED -> SENT -> (ACKED | REJECTED)`

`ACKED -> PARTIAL -> FILLED`

`ACKED -> CANCELED`

`ACKED -> EXPIRED`

Any state -> `ERROR` only for adapter/system faults (not broker business rejects).

### 12.10 Idempotency & reliability

- `client_order_id` generated upstream and reused on retries.
- Submit retry allowed only when ack is unknown; never blind-resubmit after explicit reject.
- Keep durable `intent_journal` (append-only):
  - intent created,
  - sent,
  - ack,
  - fills,
  - reconcile corrections.

### 12.11 Precision / VN market constraints hooks

Add deterministic helper functions used by adapter pre-submit:
- `normalize_tick(symbol, price) -> Decimal`
- `normalize_lot(symbol, qty) -> Decimal`
- `session_gate(now, symbol) -> bool`
- `price_band_check(symbol, side, price) -> bool`

Reject early before browser submit if any check fails.

### 12.12 Minimal test matrix for adapter contract

1. Submit LIMIT happy path -> ACKED.
2. Submit invalid tick -> REJECTED (`REJECT_INVALID_PRICE_TICK`).
3. Partial fill then full fill -> cumulative qty exact.
4. Cancel open order -> CANCELED.
5. Duplicate client_order_id retry -> no duplicate broker order.
6. Reconcile detects missing local fill -> emits synthetic fill.
7. Session closed submit attempt -> blocked pre-submit.

---

## 13) Documentation References (Nautilus)

This contract aligns with Nautilus docs concepts around:
- event-driven architecture,
- ports and adapters,
- execution flow (command -> risk -> execution -> order events),
- reconciliation and robust state handling.

Reference entry points:
- https://nautilustrader.io/docs/latest/
- https://nautilustrader.io/docs/latest/concepts/architecture/
- https://nautilustrader.io/docs/latest/integrations/

---

## 14) VPS Web-Only Reality: Unified Browser Adapter Strategy

Given current constraints (**no official VPS trading API**), implementation should treat the browser app as the temporary execution/data gateway.

### 14.1 Core decision
Build one unified component:
- `VPSWebAdapter` (ports + adapters style)
  - **Read path**: account sync (positions, cash, orders, fills)
  - **Write path**: order submit/modify/cancel

This avoids drift between separate scraping and trading bots and ensures identical selector/session handling.

### 14.2 Operational modes
- `MODE=read_only`
  - Login/session keepalive
  - Pull portfolio snapshots periodically
  - Pull order/fill updates for reconcile
  - No trade actions allowed
- `MODE=confirm_trade`
  - Generates order intents automatically
  - Requires explicit operator approval before submit
- `MODE=auto_trade_limited`
  - Limited symbol allowlist + strict max notional/risk guards
  - Mandatory reconcile after every state mutation

Default deployment mode: `read_only` then `confirm_trade`.

---

## 15) VPS Web Adapter Specification (Implementation-Ready)

### 15.1 File/module layout

```bash
trading-automation/src/execution/vps/
  adapter.py               # public port implementation
  session.py               # login/session/token/cookie lifecycle
  selectors.py             # versioned UI selectors map
  parser.py                # parse positions/orders/fills from DOM tables
  actions.py               # click/type/submit primitives
  guards.py                # pre-submit safety checks
  reconcile.py             # broker-state reconciliation helpers
```

### 15.2 Public interface
- `sync_account_state(account_id) -> AccountSnapshot`
- `sync_open_orders(account_id) -> list[OrderState]`
- `sync_fills(account_id, since_ns) -> list[FillEvent]`
- `submit(intent: OrderIntent) -> BrokerAck`
- `modify(client_order_id, ...) -> BrokerAck`
- `cancel(client_order_id) -> BrokerAck`
- `health() -> AdapterHealth`

### 15.3 Session management
- Session bootstrap at pre-open.
- Periodic heartbeat check (UI element + account identity check).
- Auto re-login on expiry with bounded retries.
- Any auth anomaly => `execution_degraded=true` and stop new orders.

### 15.4 Selector versioning
- `selectors.py` must support `v1`, `v2`, ... profiles.
- Runtime loads active selector profile from config.
- Add canary selector check in `health()` to catch UI changes early.

---

## 16) Account Sync Plan (Portfolio Auto-Tracking for Alerts)

### 16.1 Sync cadence
- During open sessions: every 30-60s
- During breaks/off-hours: every 3-10m
- Forced sync immediately after any order/fill event

### 16.2 Normalized outputs
Adapter must publish:
- `portfolio_snapshots(account_id, ts_ns, positions[], cash, nav)`
- `portfolio_symbols_current(account_id, symbols[], updated_at)`
- `execution_updates` and `fill_events`

These feed:
- alert scope resolver (`symbol_selector: portfolio`)
- risk engine
- reconcile engine

### 16.3 Staleness policy
- If account sync stale beyond threshold (e.g. 90s market hours):
  - Fire critical ops alert
  - Pause portfolio-scoped trading rules
  - Keep read-only recovery loop active

---

## 17) Trading Automation on Web App (Safe-by-Design)

### 17.1 Pre-submit guard chain (must pass all)
1. Market session gate open
2. Portfolio/account sync fresh
3. Price tick and lot normalization pass
4. Price band and slippage bounds pass
5. Risk limits pass (symbol, account, daily)
6. No unresolved reconcile mismatch for symbol/account

### 17.2 Post-submit requirements
- Immediate ack capture
- Open-order refresh
- Fill polling/reconciliation window
- Emit lifecycle events back to Nautilus bridge

### 17.3 Hard stop triggers
- Repeated selector failure
- Login/session instability
- Elevated reject rate
- Reconcile mismatch above threshold
- Daily drawdown breach

Any hard-stop trigger must set `trade_write_disabled=true` until manual clear.

---

## 18) Integration with Alert System (Custom + Portfolio-Aware)

Use the new alert artifacts:
- `docs/schemas/alert-rule.schema.json`
- `config/alerts/rules.v1.yaml`
- `tools/alerts/resolve_alert_scope.py`
- `tools/alerts/validate_alert_rules.py`

### 18.1 Dynamic coverage model
- `symbol_selector: watchlist` for thematic coverage
- `symbol_selector: portfolio` for live holdings coverage
- `symbol_selector: all` for system-level alerts

### 18.2 Critical execution alerts to enable by default
- session/auth degraded
- submit reject spike
- fill stalled
- reconcile mismatch
- account sync stale

---

## 19) Expanded Delivery Roadmap (Web-first)

### Sprint 1 — Read foundation
- Implement `VPSWebAdapter` read path only
- Persist `portfolio_snapshots` and `portfolio_symbols_current`
- Wire portfolio-scoped alert resolution

### Sprint 2 — Confirm-mode trading
- Implement submit/modify/cancel with guard chain
- Add confirm workflow and execution audit trail
- Reconcile loop after each order action

### Sprint 3 — Reliability hardening
- Selector versioning + canary checks
- Session recovery policies
- Synthetic event replay tests for reconcile correctness

### Sprint 4 — Limited auto mode
- Enable `auto_trade_limited` for allowlisted symbols
- Strict caps (max notional/day loss/order rate)
- Incident playbook + on-call style alert escalation

---

## 20) Immediate Next Tasks

1. Implement `src/execution/vps/session.py` + `selectors.py`.
2. Implement read-only sync to populate portfolio symbol cache.
3. Connect sync outputs to alert resolver runtime.
4. Add critical health alerts for adapter/session/sync staleness.
5. Run 1-week shadow mode before any live write actions.
