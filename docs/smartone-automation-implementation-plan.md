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
