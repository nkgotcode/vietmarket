# Playwright E2E (apps/web)

## Why

The app is Clerk-protected. For true E2E, we need a test-only auth bypass so Playwright can hit protected routes without real Clerk keys.

## Test-only auth bypass

Enable:

- `E2E_BYPASS_AUTH=1`
- `E2E_BYPASS_TOKEN=<random>`

Then Playwright sends:

- header `x-e2e-bypass: <token>`

The middleware and `/api/history/*` route handlers allow requests when (and only when) both env + header match.

**Never set `E2E_BYPASS_AUTH=1` in production.**

## Run locally

```bash
cd apps/web
E2E_BYPASS_TOKEN=devtoken npm run test:e2e
```

## What is tested

- `/app` renders Market overview + Headlines and supports pagination (Load more).
- `/app/symbol/VCB` renders chart controls + News section.
