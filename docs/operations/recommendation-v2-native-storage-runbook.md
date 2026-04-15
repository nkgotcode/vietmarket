# Recommendation V2 Native Storage Runbook

## Purpose
Move recommendation storage away from overloaded legacy JSON blobs and into first-class v2-native tables.

## Tables
- `recommendations` remains the primary operator object for now
- `recommendation_scorecards` stores explicit scorecard metrics per recommendation
- `promotion_decisions` stores explicit promotion semantics per recommendation

## Guarantees
- every recommendation row can be joined to a scorecard row
- every recommendation row can be joined to a promotion decision row
- API/UI layers should prefer scorecard/promotion tables over decoding `recommendation_json`

## Verification
```bash
export PG_URL='postgres://...'
bash scripts/verify_recommendation_v2_storage.sh
```

## Safety note
This is storage cleanup and semantics cleanup only. It does not re-enable paper trading.
