# VietMarket Deploy — Runbooks Index

This folder contains deployment/runbook docs for VietMarket’s infrastructure:

- Nomad cluster + ingestion jobs (candles/news)
- TimescaleDB **HA** (Patroni + etcd) as the canonical candles history store
- Public **History API** on Vultr, exposed via **Tailscale Funnel** and protected by `X-API-Key`

If you’re looking for "what do I run next", start here.

---

## 1) Nomad Cluster (Topology + Jobs)

### Topology (tailnet IPs)

- **Optiplex (Linux)**: `100.83.150.39` — Nomad server+client
- **EPYC (Linux)**: `100.103.201.10` — Nomad server+client
- **Vultr (Linux)**: `100.110.26.124` — Nomad server-only (quorum)
- **Mac mini (macOS)**: `100.100.5.40` — Nomad client-only witness/utilities

### Primary docs

- **Nomad overview**: `nomad/README.md`
- **Timescale HA (Patroni)**: `nomad/HA_TIMESCALE_RUNBOOK.md`

### Nomad job specs

Located in: `deploy/nomad/jobs/`

- Candles:
  - `vietmarket-candles-latest.nomad.hcl` (periodic)
  - `vietmarket-candles-backfill.nomad.hcl` (periodic; currently 1D only)
- News:
  - `vietmarket-news.nomad.hcl` (Vietstock → Convex)
- HA DB:
  - `etcd.nomad.hcl` (3-node DCS: optiplex + epyc + mac mini)
  - `timescaledb-ha.nomad.hcl` (2-node DB: optiplex + epyc)
  - `pg-haproxy.nomad.hcl` (2-node proxy; stable DB endpoint on :5433)

---

## 2) TimescaleDB HA (Canonical Candles History)

**Goal:** store full candle history cheaply and reliably, with automatic failover.

### Components

- **etcd** (quorum): leader election / DCS for Patroni
  - ports: 2379/2380
- **timescaledb-ha** (Patroni): Postgres + Timescale extension, replication + auto promotion
  - Postgres port: 5432
  - Patroni REST: 8008 (not required for client access)
- **pg-haproxy**: stable endpoint for clients to connect to current leader
  - listens on **5433** on both Optiplex + EPYC

### DB endpoints (clients should use HAProxy)

- Primary:
  - `postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable`
- Fallback:
  - `postgres://vietmarket:vietmarket@100.103.201.10:5433/vietmarket?sslmode=disable`

### Schema

- Schema file: `timescaledb/schema.sql`
- Apply schema via HAProxy:

```bash
psql "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable" \
  -f /home/itsnk/vietmarket/deploy/timescaledb/schema.sql
```

Full runbook:
- `nomad/HA_TIMESCALE_RUNBOOK.md`

---

## 3) Public History API (Vultr + Docker)

**Goal:** serve deep candle history for infinite scroll without putting full history in Convex.

### Summary

- Runs on **Vultr** as a Docker container using `docker compose`.
- Binds locally to `127.0.0.1:8787`.
- Exposed publicly using **Tailscale Funnel**.
- Protected by `X-API-Key` header.

### Primary doc

- `history-api/RUNBOOK.md`

---

## 4) Tailscale Notes (Serve vs Funnel)

### Working, persistent public exposure (Vultr)

On your current Tailscale CLI versions, the most reliable approach is:

```bash
# stop any prior Serve config that occupies 443
sudo tailscale serve reset

# expose local History API publicly and persist in background
sudo tailscale funnel --bg http://127.0.0.1:8787

tailscale funnel status
```

Key finding:
- `tailscale serve --bg 8787` defaults to HTTPS/443 and can conflict with Funnel’s listener ownership.

---

## 5) Hybrid Candles Architecture (Convex cache + Timescale canonical)

### Current state

- Convex currently stores candles slices and is easy to overrun on the free tier.
- Timescale HA + History API are now the intended canonical store + deep-scroll path.

### Target state

- **TimescaleDB HA**: canonical full candles history
- **Convex**: bounded “latest slice” cache for UI speed/cost control
- **History API**: paging endpoint to fetch older candles (`beforeTs`, `limit`)

### Next implementation tasks (dual-write)

> These are not fully implemented yet; this section is the checklist we will follow.

1) Ingestion: dual-write candles (optional)
   - Always upsert full history to Timescale (idempotent `PRIMARY KEY (ticker,tf,ts)`)
   - If Convex is under heavy limits, skip Convex entirely and serve candles from History API

2) History API: ensure paging matches UI
   - Endpoint already supports: `GET /candles?ticker&tf&beforeTs&limit`
   - Return newest-first; UI can reverse or append

3) Next.js chart loader
   - Load most recent from Convex
   - Page older from History API

4) Disable/limit Convex-heavy backfills
   - keep latest ingestion minimal until Convex plan upgraded

---

## 6) Troubleshooting quick map

### History API health says `db_unreachable`

- Confirm HAProxy is deployed and healthy: `nomad job status pg-haproxy`
- Confirm History API container has `PG_URL` set.
- Confirm DB endpoint reachable from Vultr:
  - `nc -vz 100.83.150.39 5433`

### Timescale HA container `Permission denied`

- Fix host dir perms on both Linux nodes:
  - `sudo chown -R 1000:1000 /opt/timescaledb-ha`

### Funnel shows tailnet-only

- Run `tailscale funnel status` (and `--json`) to see if Funnel is permitted.

---

## 7) File layout

- `deploy/README.md` — this index
- `deploy/nomad/README.md` — Nomad topology + job list
- `deploy/nomad/HA_TIMESCALE_RUNBOOK.md` — etcd + Patroni + HAProxy
- `deploy/history-api/RUNBOOK.md` — Vultr Docker + Funnel
- `deploy/timescaledb/schema.sql` — canonical candles schema
