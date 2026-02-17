# VietMarket TimescaleDB HA (Nomad + Patroni + etcd) — Runbook

This runbook documents how to run TimescaleDB with **automatic failover** on the Nomad cluster.

## Goals

- Automatic failover between **Optiplex** and **EPYC** using Patroni.
- 3-node quorum using **etcd** (Optiplex + EPYC + Mac mini witness).
- A stable client endpoint using **HAProxy** (routes to current leader).

## Topology

### Nodes
- Optiplex (server+client): `100.83.150.39`
- EPYC (server+client): `100.103.201.10`
- Mac mini (client-only witness): `100.100.5.40`

### Services
- etcd (3 members)
  - Ports: 2379 (client), 2380 (peer)
- TimescaleDB HA (2 members)
  - Postgres: 5432
  - Patroni REST: 8008
- HAProxy (2 members)
  - RW endpoint: 5433 on each node

## Nomad job files

- `deploy/nomad/jobs/etcd.nomad.hcl`
- `deploy/nomad/jobs/timescaledb-ha.nomad.hcl`
- `deploy/nomad/jobs/pg-haproxy.nomad.hcl`

## One-time host preparation

### Optiplex + EPYC

```bash
sudo mkdir -p /opt/etcd /opt/timescaledb-ha

# etcd (docker) will write into /opt/etcd
sudo chown -R root:root /opt/etcd

# timescaledb-ha container needs write perms on /opt/timescaledb-ha
# (image user is typically uid/gid 1000)
sudo chown -R 1000:1000 /opt/timescaledb-ha
```

### Mac mini witness

- etcd runs via `raw_exec` (Homebrew binary) and stores data under:
  - `~/Library/Application Support/etcd`

```bash
mkdir -p "/Users/lenamkhanh/Library/Application Support/etcd"
```

## Deploy (order matters)

Run from Optiplex:

```bash
cd /home/itsnk/vietmarket
git pull
export NOMAD_ADDR=http://100.83.150.39:4646

nomad job run deploy/nomad/jobs/etcd.nomad.hcl
nomad job status etcd

nomad job run deploy/nomad/jobs/timescaledb-ha.nomad.hcl
nomad job status timescaledb-ha

nomad job run deploy/nomad/jobs/pg-haproxy.nomad.hcl
nomad job status pg-haproxy
```

Healthy targets should show:
- etcd: `3/3`
- timescaledb-ha: `2/2`
- pg-haproxy: `2/2`

## Client connection string

Use HAProxy port 5433:

- Primary:
  - `postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable`
- Fallback:
  - `postgres://vietmarket:vietmarket@100.103.201.10:5433/vietmarket?sslmode=disable`

(HAProxy always points to the current leader.)

## Database schema

### Candles performance tuning (current)
The `candles` hypertable is tuned for high write volume + chart paging:
- Chunk time interval: **7 days** (integer ms time dimension)
- Compression: enabled, segment-by `(ticker, tf)` and order-by `ts`
- Compression policy: compress chunks older than **14 days**

A helper table `candles_latest` is maintained via trigger to support cross-sectional "latest" queries efficiently.


Apply schema via HAProxy:

```bash
psql "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable" \
  -f /home/itsnk/vietmarket/deploy/timescaledb/schema.sql
```

## How failover works

- Patroni continuously updates leader state in etcd.
- On leader failure, Patroni promotes a replica.
- HAProxy uses health checks to decide which backend is up.

### Important limitation

This setup currently uses **TCP checks** to Postgres. That means HAProxy will route to any node with an open 5432, even if it is a replica.

In practice, Patroni should keep only the leader accepting writes, but for strict leader-only routing you can upgrade the HAProxy check to a SQL check (e.g. verify `pg_is_in_recovery() = false`) or restore Patroni-REST-based checks when 8008 is reachable locally.

## Convex usage note

If Convex free-tier limits are exceeded and deployments get disabled, you can run the app in **Timescale-only** mode for candles:

- Stop the Nomad Convex candle jobs:
  - `nomad job stop -purge vietmarket-candles-latest`
  - `nomad job stop -purge vietmarket-candles-backfill`
- Point the Next.js chart loader at History API via:
  - `NEXT_PUBLIC_HISTORY_API_URL`
  - `NEXT_PUBLIC_HISTORY_API_KEY`

To make routing strictly leader-only, we have two options:
1) Ensure Patroni REST `:8008` is reachable by HAProxy (local checks), and use Patroni role-based checks.
2) Use a Postgres-aware health check (SQL) that validates `pg_is_in_recovery()` is false.

If strict RW routing is required, we should implement option (2) next.

## Troubleshooting

### etcd won’t form quorum

- If you deployed partially and need to restart from scratch:
  - Stop job: `nomad job stop -purge etcd`
  - Wipe data:
    - Optiplex+EPYC: `sudo rm -rf /opt/etcd/*`
    - Mac: delete `~/Library/Application Support/etcd/*`
  - Re-run `etcd` job.

### timescaledb-ha exits immediately with permission denied

Symptom:
- `Permission denied` creating `/home/postgres/pgdata/...`

Fix:
- `sudo chown -R 1000:1000 /opt/timescaledb-ha` on both Linux nodes.

### HAProxy accepts TCP but apps still fail

- Validate the DB exists and credentials are correct:
  - `psql ... -c 'select 1'`
- Confirm schema exists.

## Notes / Findings (from setup)

- ClickHouse setup was blocked by Nomad docker volume restrictions + container startup perms.
- Convex free tier can disable deployments entirely; workers must handle `{status:"error"}` responses.
- For public API, Tailscale Funnel is simpler than exposing DB or using Cloudflare Workers.
