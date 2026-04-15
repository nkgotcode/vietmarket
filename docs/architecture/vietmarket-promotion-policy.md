# VietMarket Promotion Policy

## Purpose
Define how recommendations should be promoted from research output into paper-trading eligibility.

## Promotion states
- `research_only`
- `watch`
- `candidate`
- `paper_eligible`
- `paper_active`
- `blocked`
- `retired`

## Hard requirements before paper eligibility
A recommendation may only become `paper_eligible` if all of these are true:

1. system health is healthy
2. evidence confidence clears threshold
3. model confidence clears threshold
4. execution suitability clears threshold
5. expected utility is positive after cost proxy
6. regime policy allows the setup
7. calibration cohort has sufficient sample size

## Required evidence sources
Promotion must reference durable DB artifacts, not prompt text:
- forward-outcome labels
- calibration buckets
- regime cohort metrics
- liquidity cohort metrics
- score version
- policy version

## Operator policy right now
Paper trading remains disabled until these promotion semantics are implemented and verified.
