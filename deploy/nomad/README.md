# VietMarket Nomad Deploy

This folder documents Nomad usage for VietMarket ingestion + HA DB.

## Topology

### Nodes (tailnet IPs)
- Optiplex (Linux): `100.83.150.39` — Nomad server+client
- EPYC (Linux): `100.103.201.10` — Nomad server+client
- Vultr VPS (Linux): `100.110.26.124` — Nomad server-only (quorum)
- Mac mini (macOS): `100.100.5.40` — Nomad client-only (witness / utilities)

## Jobs

### Corporate actions / dividends

- `vietmarket-corporate-actions-ingest` (batch + periodic)
  - Scrapes VietstockFinance events calendar (`/lich-su-kien.htm`) and upserts into Timescale `corporate_actions`.
  - Runtime fallbacks: requests/session retries → `curl_cffi` → Playwright POST → Playwright table scrape.
  - Reconciles unknown tickers into `symbols` before CA upsert to avoid FK-abort drops.
  - Date extraction supports both JSON fields (`GDKHQDate`/`NDKCCDate`/`Time`) and table-text fallback.
  - Runs on EPYC.

### Candles (periodic batch)
- `jobs/vietmarket-candles-timescale-latest.nomad.hcl` — near-real-time refresh into Timescale (multi-tf windowed)
- `jobs/vietmarket-candles-timescale-backfill.nomad.hcl` — **1D** full-history backfill into Timescale (cursor persisted)
- `jobs/vietmarket-candles-timescale-backfill-1h.nomad.hcl` — **1H** intraday backfill (attempt full history; provider-limited)
- `jobs/vietmarket-candles-timescale-backfill-15m.nomad.hcl` — **15m** intraday backfill (attempt full history; provider-limited)

Notes:
- Backfill jobs rely on cursor persistence under `/opt/nomad/data/vietmarket-cursors` on each Linux client.

### Derived market/fundamental surfaces (periodic batch)
- `jobs/vietmarket-derived-market-sync.nomad.hcl` — consolidated 30m sync on EPYC
  - Creates/syncs Timescale tables:
    - `financials` (from `fi_latest`)
    - `fundamentals` (latest-per-(ticker,metric))
    - `technical_indicators` (latest close/sma20/sma50/ema20 by ticker/tf)
    - `indicators` (normalized KV indicator rows)
    - `market_stats` (candles/CA summary metrics + KPIs)
  - Script: `packages/ingest/vn/derived_market_sync_pg.py`
  - KPI metrics now written into `market_stats` include:
    - coverage (`candles_eligible_total/with_candles/missing`, `candles_coverage_pct`)
    - per-tf rows/tickers (`candles_1d_*`, `candles_1h_*`, `candles_15m_*`)
    - frontier diagnosis (`candles_frontier_status`, `candles_frontier_lag_ms`)

### News
- `jobs/vietmarket-news.nomad.hcl` — Vietstock archive → Convex sync

### History DB (Timescale HA)
See: `HA_TIMESCALE_RUNBOOK.md`

- `jobs/etcd.nomad.hcl` — etcd quorum for Patroni
- `jobs/timescaledb-ha.nomad.hcl` — TimescaleDB HA (Patroni)
- `jobs/pg-haproxy.nomad.hcl` — stable DB endpoint on port 5433

## Env / Config notes

- Convex URL: `https://opulent-hummingbird-838.convex.cloud`
- Mac mini should remain **client-only** (no server).
- Prefer using **meta constraints** to target Mac mini (e.g. `meta.role=witness`).

## Operational gotchas (findings)

### Cursor persistence for periodic writers
For sharded periodic jobs (candles latest/backfill), **persist cursors on the host** or they will reprocess the same tickers every run.

Pattern used in job specs:
- host: `/opt/nomad/data/vietmarket-cursors`
- container: `/opt/nomad/data/vietmarket-cursors`

### Intraday scale
Full intraday backfill can grow very large. Prefer efficient query patterns (keyset paging) and use the `candles_latest` snapshot table for cross-sectional “latest”.

- Nomad Docker driver may block host mounts unless docker volumes are enabled in client config.
- Stateful services require correct host dir permissions (`/opt/...`).
- Convex free plan can disable deployments; ingestion/repair workers should handle `{status:"error"}` HTTP responses gracefully.

## Quick verification

```bash
# Derived tables status
psql "$PG_URL" -Atc "
select 'financials',count(*) from financials
union all select 'fundamentals',count(*) from fundamentals
union all select 'technical_indicators',count(*) from technical_indicators
union all select 'indicators',count(*) from indicators
union all select 'market_stats',count(*) from market_stats;
"

# CA status
psql "$PG_URL" -Atc "
select count(*) as ca_rows,
       count(*) filter (where ex_date is not null) as ex_nonnull,
       count(*) filter (where record_date is not null) as record_nonnull,
       count(*) filter (where pay_date is not null) as pay_nonnull,
       max(ingested_at) as newest_ingested_at
from corporate_actions;
"
```

## References

- Timescale HA runbook: `HA_TIMESCALE_RUNBOOK.md`
- History API runbook: `../history-api/RUNBOOK.md`
