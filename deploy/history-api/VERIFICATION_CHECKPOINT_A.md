# Checkpoint A Verification (non-Docker)

Date: 2026-02-19

## Scope verified
- `GET /v1/analytics/overview`
- `GET /v1/context/:ticker`
- `GET /v1/sentiment/overview`
- `GET /v1/sentiment/:ticker`
- `GET /v1/overall/health`

Plus error contracts:
- unauthorized -> `401` + `error=unauthorized`
- invalid ticker -> `400` + `error=invalid_ticker`
- invalid window -> `400` + `error=invalid_window_days`

## Verification method
- Non-Docker runtime only.
- Started `deploy/history-api/server.mjs` locally.
- Connected to existing PG/Timescale endpoint.
- Ran reproducible script: `deploy/history-api/tests/run_contract_non_docker.sh`.

## Artifacts
- `deploy/status/checkpoint-a-server.log`
- `deploy/status/checkpoint-a-verify.log`
- `deploy/status/checkpoint-a-endpoints/*.json`

## Limitation
- This is contract verification against a live/shared database snapshot, not an isolated seeded dataset.
- Therefore payload values can drift over time, but envelope/status/error contract checks are auditable and reproducible.
