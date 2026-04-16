# Grade Semantics Reference

This document defines the authoritative operator-facing semantics for the VietMarket grading reset.

## Purpose

The grading reset exists to replace overloaded score terms with labels that each mean exactly one thing.

Core rule:
- one number or grade = one meaning
- analysis truth must stay separate from policy truth
- policy truth must stay separate from portfolio admission truth

## Primary grades

### Opportunity Grade
Question answered:
- How attractive is the setup on expected opportunity strength alone?

This grade should reflect:
- expected edge
- benchmark-relative or regime-relative opportunity
- cross-sectional attractiveness for the chosen horizon

This grade should **not** directly encode:
- data completeness
- tradability
- policy status

### Evidence Grade
Question answered:
- How trustworthy are the inputs behind this setup?

This grade should reflect:
- freshness
- completeness
- feature missingness
- source health
- coverage sufficiency

This grade should **not** mean expected return.

### Tradability Grade
Question answered:
- How realistically can this be traded without poor implementation quality?

This grade should reflect:
- turnover
- volume
- capacity fit
- implementation friction
- tradability_index

This grade replaces the old habit of treating `liquidity_score` as a vague catch-all.

### Risk Containment Grade
Question answered:
- How controllable is the downside profile if the setup is wrong?

This grade should reflect:
- volatility
- fragility
- event distortion risk
- downside instability

This grade should **not** be treated as policy approval.

## Reliability dimensions

### Forecast Reliability
Question answered:
- How historically reliable have similar setups been in comparable conditions?

### Evidence Reliability
Question answered:
- How reliable are the observed inputs and feature set for this specific name?

### Execution Reliability
Question answered:
- How likely is acceptable implementation quality if acted on?

## State semantics

The system should preserve separate truths:
- analytical quality
- operational/policy permission
- portfolio admission

Example:
- a ticker can have strong Opportunity Grade
- weak Evidence Grade
- poor Tradability Grade
- and still be policy blocked for unrelated reasons

That is not a contradiction. It is the intended model.

## Deprecated terminology

The following terms are deprecated as operator-facing primary semantics unless explicitly labeled as legacy:

- `confidence`
  - too overloaded
  - must be replaced by labeled reliability dimensions

- `liquidity_score`
  - too ambiguous
  - current code path aliases it from execution scoring
  - should be replaced by explicit tradability concepts

- naked `model_confidence`
  - acceptable as an internal field during migration
  - not acceptable as the sole operator-visible confidence concept

- naked `decision_score`
  - acceptable as a compatibility artifact during migration
  - not acceptable as the main explanation surface

## UI rules

The operator UI must show labels, not ambiguous numerics.

Required labels:
- Opportunity Grade
- Evidence Grade
- Tradability Grade
- Risk Containment Grade
- Forecast Reliability
- Evidence Reliability
- Execution Reliability

Forbidden default UI patterns:
- one unlabeled `confidence` chip
- one unlabeled `liquidity_score` chip
- one dominant master score with unlabeled supporting metrics

## Migration note

During transition, legacy fields may still exist in storage or compatibility APIs.

They must be clearly marked as:
- legacy
- compatibility-only
- not authoritative for the grade reset
