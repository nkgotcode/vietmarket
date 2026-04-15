# VietMarket History API Contracts (v1)

Production endpoints introduced:

- `GET /v1/analytics/overview`
- `GET /v1/context/:ticker`
- `GET /v1/sentiment/overview?windowDays=7&limit=30`
- `GET /v1/sentiment/:ticker?windowDays=30`
- `GET /v1/overall/health`

## Common

- Auth: `x-api-key` required
- Success envelope: `{ ok: true, version: "v1", data: ... }`
- Error envelope: `{ ok: false, error: "<code>", message?: "<detail>" }`
- Stable error codes:
  - `unauthorized`
  - `invalid_ticker`
  - `invalid_window_days`
  - `invalid_limit`
  - `internal_error`

## Freshness / robustness

- `analytics/overview` and `overall/health` return `generated_at`
- `overall/health` includes repair-queue counts and frontier metrics
- `analytics/overview` includes:
  - candles totals + per-TF rows/tickers
  - coverage totals (`eligible_total/with/missing`, `coverage_pct`)
  - CA totals (`ex/record/pay` non-null)
  - derived-table row totals

## Sentiment model

Current production scoring is deterministic lexical scoring over fetched article title+text:

- positive terms increment score by `+1`
- negative terms decrement score by `-1`

Ticker sentiment aggregates are computed from `article_symbols` joins across rolling windows.

## Web app proxies

`apps/web` routes proxy these endpoints with Clerk auth:

- `/api/analytics/overview`
- `/api/context/[ticker]`
- `/api/sentiment/overview`
- `/api/sentiment/[ticker]`
- `/api/overall/health`
