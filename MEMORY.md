# MEMORY.md

## Environment / preferences
- nk prefers a casual vibe.
- Memory preference: automatically save system setup + automations; ask before saving other things.
- After FTS is fixed, enable session transcript indexing for memory search (`agents.defaults.memorySearch.experimental.sessionMemory: true`, `sources: ["memory","sessions"]`).

## System setup
- Node.js best practice on this Mac: use `nvm` as the single source of truth; avoid installing Node via Homebrew to prevent PATH conflicts.
- Current baseline Node used for Clawdbot: v22.14.0 (npm 11.8.0), managed by nvm.
- OpenClaw Gateway runs locally via LaunchAgent on port **18789** (Dashboard: http://127.0.0.1:18789/).
- Python: `python3` is available via Homebrew; `python` is shimmed to `python3` (symlink in `/usr/local/bin/python` + zsh alias) for convenience.
- System Python does **not** have `pytz` installed; prefer `zoneinfo` or shell `date`, or install `pytz` explicitly if needed.
- Playwright is installed on the Mac mini (Node module present; browser binaries cached under `~/.cache/ms-playwright/`).
- Memory search/indexing: SQLite **FTS5 currently unavailable** (`no such module: fts5`). Homebrew `node@22` install attempt failed on macOS 12 (“Tier 3”).

## Automation
- Daily Clawdbot auto-update cron job (updates npm global clawdbot and restarts gateway):
  - Job name: Daily Clawdbot update
  - Job id: 06006d43-f249-4dcd-ac1c-78235a6a7f8f
  - Schedule: 3:00 AM Asia/Ho_Chi_Minh

- Hourly memory distill (auto-save durable context to `MEMORY.md` + daily log; skips if no session changes):
  - Job name: Hourly memory distill → MEMORY.md + daily log
  - Job id: b1c6d976-66d2-44be-a32c-f0dd85610e6c
  - Schedule: minute 05, every hour (Asia/Ho_Chi_Minh)
  - State file: `/Users/lenamkhanh/clawd/memory/auto-distill-state.json`

- Simplize ingest + daemon jobs:
  - Simplize ingest (Q) every 30m
    - Job id: 3572b52a-5026-4e6e-923a-d0d061079f4e
  - Simplize API daemon keepalive (every 5m)
    - Job id: c0894d11-d10e-45b0-979d-8175529d41f2
  - Simplize API watchdog (every 2m)
    - Job id: 57be7e74-cf29-4dd4-be01-4d18c474bf76

- Vietstock RSS relay refresh cron job:
  - Job name: Vietstock RSS relay refresh (15m)
  - Job id: fc2e2adc-fe91-4547-b09a-0b7235eb3914
  - Schedule: every 15 minutes (Asia/Ho_Chi_Minh)

- Vietstock archive maintenance cron job (RSS ingest + fetch):
  - Job name: Vietstock archive: RSS ingest + fetch (15m)
  - Job id: 04462c22-984f-422a-ab9d-d078a0cd286d
  - Schedule: every 15 minutes (Asia/Ho_Chi_Minh)

- Vietstock archive backfill crawl cron job:
  - Job name: Vietstock archive: backfill crawl (hourly)
  - Job id: 7fcaabc5-3f81-4456-bd6b-249233970633
  - Schedule: hourly (Asia/Ho_Chi_Minh)
  - Note: if `kv.backfill.done`/`control.backfill_done` is set, the backfill step is skipped.

## News tracking (local-first)
- Vietstock RSS relay/cache served locally at http://127.0.0.1:18999/ (needed because Vietstock blocks blogwatcher/Go default user-agent).
- Start the relay server via launchd (LaunchAgent: ~/Library/LaunchAgents/com.clawdbot.vietstock-relay.plist).
- If Vietstock archive RSS ingest shows `Connection refused` / `URLError: [Errno 61]` when fetching the relay index at `http://127.0.0.1:18999/`, the relay server is likely not running/not listening (distinct from `vietstock-relay-refresh`, which only refreshes cache).
- `vietstock-archive status --json` does **not** accept a positional path argument (e.g. `.`); run it from the intended working directory.
- Day exports (for sharing/reading outside chat) are stored under: `/Users/lenamkhanh/clawd/exports/vietstock/YYYY-MM-DD/` (typically `*-full.md` + `index.json`, optionally zipped).
- Plan: local-only archive first (HTML + cleaned text + SQLite), add syncing + dashboard later via Clawdbot Gateway.

## Simplize market data (reverse-engineering)
- OHLCV endpoint works (public): `https://api2.simplize.vn/api/historical/prices/ohlcv` (params include `ticker`, `type`, `interval`, `size`, `to`).
- Financial statements endpoints referenced in the frontend (`/api/company/fi/*`, `/api/company/fi/period/select`, `/api/company/view/fi-data`) did **not** work unauthenticated in probing (404/405; POST to `/api/company/view/fi-data` returned 500) → likely requires auth and/or specific payload/headers.
