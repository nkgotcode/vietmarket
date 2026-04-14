# Phase 9C Telegram Operator Workflows Runbook

## Purpose
Phase 9C upgrades operator delivery from format-only payloads to durable Telegram dispatch workflows with a delivery ledger.

Outputs include:
- `delivery_events` rows for daily brief, intraday alerts, and approval queue dispatches
- Telegram Bot API send support when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- safe dry-run behavior when Telegram credentials are absent

## Verification
```bash
export PG_URL='postgres://...'
export TELEGRAM_BOT_TOKEN='123:abc'   # optional for real sends
export TELEGRAM_CHAT_ID='123456789'   # optional for real sends
bash scripts/verify_phase9c_telegram_operator_workflows.sh
```

## Expected results
- `delivery_events` contains fresh rows for:
  - `daily_brief`
  - `intraday_alerts`
  - `approval_queue`
- `delivery_status` is `sent` when Telegram credentials are valid
- `delivery_status` is `dry_run` when credentials are intentionally absent
