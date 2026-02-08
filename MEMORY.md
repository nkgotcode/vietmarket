# MEMORY.md

## Environment / preferences
- nk prefers a casual vibe.
- Memory preference: automatically save system setup + automations; ask before saving other things.
- After FTS is fixed, enable session transcript indexing for memory search (`agents.defaults.memorySearch.experimental.sessionMemory: true`, `sources: ["memory","sessions"]`).

## System setup
- Node.js best practice on this Mac: use `nvm` as the single source of truth; avoid installing Node via Homebrew to prevent PATH conflicts.
- Current baseline Node used for Clawdbot: v22.14.0 (npm 11.8.0), managed by nvm.
- OpenClaw Gateway runs locally via LaunchAgent on port **18789** (Dashboard: http://127.0.0.1:18789/).
- `python` is not available in PATH on this host (use `node`/shell for automations).
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

- Vietstock RSS relay refresh cron job:
  - Job name: Vietstock RSS relay refresh (15m)
  - Job id: fc2e2adc-fe91-4547-b09a-0b7235eb3914
  - Schedule: every 15 minutes (Asia/Ho_Chi_Minh)

## News tracking (local-first)
- Vietstock RSS relay/cache served locally at http://127.0.0.1:18999/ (needed because Vietstock blocks blogwatcher/Go default user-agent).
- Start the relay server via launchd (LaunchAgent: ~/Library/LaunchAgents/com.clawdbot.vietstock-relay.plist).
- Plan: local-only archive first (HTML + cleaned text + SQLite), add syncing + dashboard later via Clawdbot Gateway.
