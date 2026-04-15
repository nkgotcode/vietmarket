# Promotion Policy Gate Runbook

## Purpose
This runbook documents the explicit gate between recommendation semantics and paper-trading admission.

## Tables
- `promotion_policy_versions`
- `paper_trade_admissions`

## Key rule
`paper_eligible` in recommendation semantics is not enough by itself.
A recommendation may only reach paper trading if a row in `paper_trade_admissions` is created with:
- `admission_status = 'admitted'`
- `paper_trading_enabled = true`
- policy and threshold checks satisfied

## Current default
The default promotion policy keeps:
- `paper_trading_enabled = false`

So the gate remains closed by default, even for otherwise strong recommendations.

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_promotion_policy_gate.sh
```
