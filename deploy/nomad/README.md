# VietMarket Nomad Deploy

## Topology (chosen)
- Nomad servers (3): optiplex (linux), epyc (linux), vultr-vps (linux)
- Nomad clients: optiplex, epyc, mac-mini (macOS)

## Notes
- Mac mini should run client-only (no quorum risk).
- Candles workers run on linux clients (docker driver).
- News sync (Vietstock archive → Convex) runs on mac-mini via exec driver.

## Env
- CONVEX_URL: https://opulent-hummingbird-838.convex.cloud
- SHARD_COUNT: 12
- latest stale: 10m
- deep stale: 30m

## Files
- `nomad/server.hcl` / `nomad/client.hcl`: node configs (templates)
- `jobs/vietmarket-candles.nomad.hcl`: candles workers (12 shards)
- `jobs/vietmarket-news.nomad.hcl`: vietstock news sync (mac-mini)
