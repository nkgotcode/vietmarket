# Promotion operator control + writable-primary verification runbook

## Purpose

This runbook gives operators one place to verify:

1. which promotion policy is active,
2. what the latest admission decisions were,
3. whether the current `PG_URL` / `DATABASE_URL` points at a writable primary.

This is the final safety seam before any live write-path verification.

## Operator UI / API

### UI
- Page: `/app/operator-control`

### API
- Route: `/api/brain/operator-control`

The payload includes:
- latest cycle metadata,
- DB target status (`transaction_read_only`, `pg_is_in_recovery()`, writable-primary verdict),
- active promotion policy version,
- latest promotion-gate worker run,
- admission counts and latest admission rows.

## Writable-primary verification

Run:

```bash
scripts/verify_writable_primary.sh
```

Expected success characteristics:
- `transaction_read_only = off`
- `pg_is_in_recovery() = f`
- script exits 0 with `Writable primary confirmed`

If the script fails:
- do **not** run migrations,
- do **not** run full supervisor write-path verification,
- repoint `PG_URL` / `DATABASE_URL` to the writable primary.

## Safe live verification order

After writable-primary verification passes:

```bash
scripts/verify_scoring_v2.sh
scripts/verify_recommendation_v2_storage.sh
scripts/verify_promotion_policy_gate.sh
```

## Current policy expectation

Even after writable-primary verification passes, the default promotion policy still keeps:

- `paper_trading_enabled = false`

So admissions should still explain why the paper-trading gate is closed unless the policy is intentionally changed.
