# VietMarket History API (Vultr) — Runbook

This deploys the public **History API** on the Vultr VPS and connects it to the private **TimescaleDB HA** cluster (Optiplex + EPYC) via HAProxy.

- Runtime: Docker (compose)
- Auth: `X-API-Key` header
- DB: TimescaleDB HA (Patroni) behind HAProxy on port **5433**
- Public exposure: **Tailscale Funnel**

## Architecture

- TimescaleDB HA runs on tailnet-only nodes:
  - Optiplex `100.83.150.39`
  - EPYC `100.103.201.10`
  - HAProxy runs on both, listening on `:5433`
- History API runs on Vultr, binds `127.0.0.1:8787`, and is published via Funnel.

## Prereqs (Vultr)

1) Vultr must be on the tailnet (Tailscale installed + logged in).
2) Docker + Compose plugin installed.

## Install Docker (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## Deploy History API

```bash
sudo mkdir -p /opt/vietmarket-history-api
sudo chown -R $USER:$USER /opt/vietmarket-history-api
cd /opt/vietmarket-history-api
```

### Create `.env`

```bash
cat > .env <<'ENV'
API_KEY=REPLACE_WITH_LONG_RANDOM

# Prefer optiplex HAProxy, fall back to epyc HAProxy if needed.
# (You can swap to EPYC if Optiplex is down.)
PG_URL=postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable
ENV
```

### Create `docker-compose.yml`

```bash
cat > docker-compose.yml <<'YML'
services:
  history-api:
    image: ghcr.io/nkgotcode/vietmarket-history-api:main
    restart: unless-stopped
    environment:
      PORT: "8787"
      API_KEY: "${API_KEY}"
      PG_URL: "${PG_URL}"
    ports:
      - "127.0.0.1:8787:8787"
YML
```

### Start

```bash
docker compose pull
docker compose up -d

docker compose ps
curl -sS http://127.0.0.1:8787/healthz
```

## Expose publicly via Tailscale Funnel

This repo/project uses the modern Tailscale CLI behavior where `funnel` can directly proxy a localhost URL.

**Important:** `tailscale serve --bg 8787` defaults to HTTPS/443 and can conflict with Funnel listener ownership. The working approach is to run Funnel directly.

```bash
# Stop any prior serve config that may occupy :443
sudo tailscale serve reset

# Start Funnel in the background (public)
sudo tailscale funnel --bg http://127.0.0.1:8787

tailscale funnel status
```

Test externally:

```bash
curl -sS https://<your-vultr-host>.<tailnet>.ts.net/healthz

curl -sS -H "x-api-key: REPLACE_WITH_LONG_RANDOM" \
  "https://<your-vultr-host>.<tailnet>.ts.net/candles?ticker=VNINDEX&tf=1d&limit=5"

## Query patterns (recommended)

### Chart paging (per ticker)
Use keyset pagination (fast with PK on `candles(ticker, tf, ts)`):
- Newest page: `ORDER BY ts DESC LIMIT N`
- Next page: `AND ts < <cursor_ts> ORDER BY ts DESC LIMIT N`

### Latest snapshot (cross-sectional)
Prefer reading from `candles_latest` (exact latest row per ticker+tf) instead of scanning `candles`.

### Time-bounded cross-sectional scans
Always bound by time and tf, e.g. `WHERE tf='15m' AND ts BETWEEN from_ms AND to_ms`.

### Corporate actions / dividends
- `GET /corporate-actions/latest?limit=50`
- `GET /corporate-actions/latest?limit=50&beforeExDate=YYYY-MM-DD&beforeId=<id>`

- `GET /corporate-actions/by-ticker?ticker=FPT&limit=50`
- `GET /corporate-actions/by-ticker?ticker=FPT&limit=50&beforeExDate=YYYY-MM-DD&beforeId=<id>`

These use keyset pagination ordered by `(ex_date desc, id desc)`.

### News endpoints + pagination
- `GET /news/latest?limit=50`
- `GET /news/latest?limit=50&beforePublishedAt=<ISO>&beforeUrl=<url>`

- `GET /news/by-ticker?ticker=VCB&limit=50`
- `GET /news/by-ticker?ticker=VCB&limit=50&beforePublishedAt=<ISO>&beforeUrl=<url>`

These use keyset pagination ordered by `(published_at desc, url desc)`.
```

## Common Issues

### `{"ok":false,"error":"db_unreachable"}`

Checklist:

1) Confirm container has `PG_URL`:
```bash
docker compose exec history-api sh -lc 'echo "$PG_URL"'
```

2) Confirm Vultr can reach HAProxy:
```bash
nc -vz 100.83.150.39 5433
nc -vz 100.103.201.10 5433
```

3) Confirm HAProxy checks do **not** depend on Patroni `:8008` over tailnet.
   - Current job uses **TCP checks** to Postgres.

### Funnel stays tailnet-only

- Ensure Funnel is enabled for your tailnet/account.
- Use `tailscale funnel status` for clues.

## Security notes

- Keep DB tailnet-only.
- Protect API with `X-API-Key`.
- Rotate the API key periodically.
