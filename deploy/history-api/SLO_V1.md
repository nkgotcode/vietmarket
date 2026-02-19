# VietMarket History API — SLO (v1 endpoints)

Scope:
- `GET /v1/analytics/overview`
- `GET /v1/context/:ticker`
- `GET /v1/sentiment/overview`
- `GET /v1/sentiment/:ticker`
- `GET /v1/overall/health`

## SLI definitions

1. **Availability SLI**
   - Good event: HTTP status < 500 for v1 routes.
   - Window: rolling 28 days.

2. **Latency SLI (p95)**
   - Good event: request duration <= 750ms.
   - Window: rolling 28 days.

3. **Data freshness SLI**
   - Good event: `candles_frontier_lag_ms <= 4h`.
   - Window: rolling 24h.

4. **Coverage SLI**
   - Good event: `candles_coverage_pct >= 95`.
   - Window: rolling 24h.

## SLO targets

- Availability: **99.5%** (error budget ~3h 21m / 28d)
- Latency p95: **99.0%** of requests under 750ms
- Freshness: **99.0%** of checks under 4h lag
- Coverage: **99.5%** of checks at or above 95%

## Burn-rate response policy

- Page if 2h burn rate > 14x on availability or freshness.
- Ticket if 24h burn rate > 3x on latency or coverage.
- Freeze non-critical deploys if error budget consumed > 50% inside first half of window.

## Ownership and runbook

- Primary owner: VietMarket ingestion/oncall.
- First investigation doc: `deploy/history-api/RUNBOOK.md`.
- Alert definitions: `deploy/monitoring/history-api-v1-alerts.yaml`.

## Reporting cadence

- Daily dashboard review during market days.
- Weekly SLO rollup posted to engineering notes.
