# MEMORY.md

## Environment / preferences
- nk prefers a casual vibe.
- Memory preference: automatically save system setup + automations; ask before saving other things.

## System setup
- Node.js best practice on this Mac: use `nvm` as the single source of truth; avoid installing Node via Homebrew to prevent PATH conflicts.
- Current baseline Node used for Clawdbot: v22.14.0 (npm 11.8.0), managed by nvm.

## Automation
- Daily Clawdbot auto-update cron job (updates npm global clawdbot and restarts gateway):
  - Job name: Daily Clawdbot update
  - Job id: 06006d43-f249-4dcd-ac1c-78235a6a7f8f
  - Schedule: 3:00 AM Asia/Ho_Chi_Minh
