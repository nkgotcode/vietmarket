# VietMarket Scoring + Supervisor Redesign Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign VietMarket’s scoring, confidence, ranking, recommendation, and paper-trading workflow so operator-visible outputs are empirically defensible, auditable, and safe enough to trust as decision support.

**Architecture:** Replace the current single heuristic “Phase 3 score + confidence + inverted priority” pipeline with a layered decision system: deterministic feature generation, regime-aware model inputs, explicit alpha/quality/risk/executability subscores, empirically calibrated confidence, policy-gated recommendation states, and evaluation-first promotion into paper trading. Make every score explainable from durable DB artifacts and every promotion step depend on measured historical performance rather than intuition or prompt prose.

**Tech Stack:** Timescale/Postgres, Python supervisor services, deterministic feature builders, SQL/Python evaluation jobs, Next.js operator surfaces, Nomad periodic jobs, Hermes only for bounded narrative synthesis after deterministic scoring.

---

## Why this redesign is necessary

The current implementation is operationally useful but not yet trustworthy enough for trade-like decisions.

### Current trust gaps found in code

1. **Phase 3 total score is a hand-tuned weighted heuristic**
   - `packages/supervisor/signals/common.py`
   - `packages/supervisor/signals/rank_candidates.py`
   - Total score is a weighted average of per-cycle normalized family scores, then multiplied by 100.
   - This is ranking-by-design, not an empirically validated expected-return model.

2. **Confidence is mostly evidence-availability confidence, not outcome confidence**
   - `packages/supervisor/signals/trend.py`
   - `packages/supervisor/signals/momentum.py`
   - `packages/supervisor/signals/catalyst.py`
   - `packages/supervisor/signals/fundamentals.py`
   - `packages/supervisor/signals/liquidity.py`
   - `packages/supervisor/signals/risk.py`
   - Family confidence values are assigned from field presence / recency / bucket availability, then averaged.
   - This does not answer the operator question: “How likely is this setup to outperform over the stated horizon?”

3. **Priority is just inverted score**
   - `packages/supervisor/theses/generate_theses.py`
   - `suggested_priority = max(0, 100 - int(total_score))`
   - This is not a separate prioritization layer. It is only a re-encoding of the same heuristic score.

4. **Recommendation status is derived from bucket thresholds rather than measured utility**
   - `packages/supervisor/signals/rank_candidates.py`
   - `packages/supervisor/recommendations/generate_recommendations.py`
   - `high_conviction` / `actionable` thresholds are fixed rules on score + confidence, not calibrated thresholds chosen from evaluation results.

5. **Evaluation is too naive to support calibration claims**
   - `packages/supervisor/reports/evaluate_recommendations.py`
   - `packages/supervisor/reports/calibration.py`
   - Current outcome logic reduces recommendations to sign of latest-cycle `ret_5d`.
   - Current calibration logic is basically `positive_rate`, not proper calibration or horizon-aware performance attribution.

6. **Paper trading was downstream of untrusted ranking logic**
   - `packages/supervisor/orchestration/run_supervisor_cycle.py`
   - `packages/supervisor/portfolio/paper_order_engine.py`
   - The paper portfolio path is too close to the recommendation path. It needs a proving gate between score generation and portfolio deployment.

---

## Redesign principles

### Principle 1: Separate ranking, confidence, and actionability
Do not use one score to mean all of these:
- alpha strength
n- evidence quality
- execution suitability
- risk acceptability
- portfolio priority

Each should be represented explicitly.

### Principle 2: Confidence must be empirical
Confidence shown to operators must come from measured historical behavior such as:
- bucket hit rate
- calibration curve
- forward return distribution
- drawdown distribution
- stability across regimes

### Principle 3: Recommendations should optimize expected utility, not score aesthetics
Move from “high score = good” to decision metrics such as:
- expected return
- downside risk
- expected Sharpe-like edge
- probability of outperforming benchmark / regime baseline
- expected utility after slippage, liquidity, and policy constraints

### Principle 4: Paper trading must be a promotion stage, not the default consumer of raw recommendations
A name should reach paper trading only after:
- quality gates pass
- model/replay evidence clears thresholds
- execution suitability passes
- regime policy allows it

### Principle 5: Hermes should narrate, not decide core arithmetic truth
Hermes can still synthesize and explain. It should not be the source of score math, confidence math, or action thresholds.

---

## Target operating model

## Layer A — Feature Plane
Keep deterministic feature builders, but convert them from “signal families” into durable feature sets.

### Feature families to preserve or improve
- trend features
- momentum features
- catalyst/event features
- fundamentals freshness/quality features
- liquidity / capacity features
- risk / volatility / stability features
- regime-context features
- sector-relative strength features
- cross-sectional rank features

### New requirement
Persist raw features separately from scored outputs so future models can be rebuilt without re-deriving interpretation from old prose.

Likely additions:
- `feature_snapshots`
- `feature_definitions`
- `feature_lineage`

---

## Layer B — Label + Evaluation Plane
Add durable forward-return labels and benchmark-relative labels.

### Labels to compute
For each ticker-cycle pair:
- forward return 1d
- forward return 3d
- forward return 5d
- forward return 10d
- forward return 20d
- forward max drawdown
- forward max favorable excursion
- sector-relative excess return
- regime-relative excess return
- liquidity-adjusted return proxy

### Purpose
This makes it possible to measure:
- whether features predict anything
- whether scores are calibrated
- whether thresholds should differ by regime / liquidity bucket / sector

Likely additions:
- `recommendation_labels`
- `ticker_forward_outcomes`
- `benchmark_snapshots`

---

## Layer C — Model / Score Plane
Replace one heuristic total score with multiple explicit subscores.

### Proposed score types
1. **alpha_score**
   - predicted opportunity strength
   - cross-sectional expected edge for the chosen horizon

2. **quality_score**
   - data completeness, freshness, and feature reliability
   - should absorb what current “confidence” partially tries to do

3. **risk_score**
   - downside / instability / volatility / event risk

4. **execution_score**
   - liquidity, turnover, spread proxy, capacity suitability

5. **policy_score**
   - whether the idea is allowed under current system/risk rules

6. **composite_decision_score**
   - final action-ranking metric derived from the above
   - not shown alone without its components

### Candidate status should become policy-driven
Possible statuses:
- `research_only`
- `watch`
- `candidate`
- `paper_eligible`
- `paper_active`
- `blocked`
- `retired`

These should be produced from explicit gates, not bucket prose.

---

## Layer D — Confidence Plane
Confidence should be split into three operator-visible concepts.

### 1. Evidence confidence
“How complete and reliable are the inputs?”
- freshness
- missing-feature rate
- stale fundamentals
- degraded ingest state
- low article coverage

### 2. Model confidence
“How historically reliable is this score bucket in comparable conditions?”
- empirical hit rate by decile
- calibration by regime
- confidence interval width
- sample size

### 3. Execution confidence
“If we acted, how likely are we to get acceptable implementation quality?”
- liquidity bucket
- capacity fit
- estimated slippage proxy
- event distortion risk

### UI rule
Do not show a single naked confidence number without labeling which confidence it is.

---

## Layer E — Recommendation Plane
Recommendations should be generated deterministically from scored + calibrated artifacts first, then narrated by Hermes second.

### New recommendation object should include
- `alpha_score`
- `quality_score`
- `risk_score`
- `execution_score`
- `composite_decision_score`
- `evidence_confidence`
- `model_confidence`
- `execution_confidence`
- `expected_return_5d`
- `expected_drawdown_5d`
- `edge_vs_benchmark_5d`
- `recommended_state`
- `promotion_reason_json`
- `block_reason_json`
- `degradation_reason_json`
- `narrative_json` (Hermes-generated, optional)

### Recommendation text generation rule
Hermes may only render narrative from the durable object above. Hermes should not invent the actual score math.

---

## Layer F — Portfolio / Paper Trading Plane
Paper trading must become a proving environment.

### Promotion rules
A recommendation enters paper trading only if:
- system health is healthy
- evidence confidence >= threshold
- model confidence >= threshold
- execution score >= threshold
- expected utility > 0 after cost proxy
- regime policy allows the side / style
- candidate has passed minimum sample-backed performance gate in its cohort

### Portfolio construction redesign
Move from fixed notional per approved recommendation to portfolio construction using:
- volatility-scaled sizing
- liquidity cap
- sector exposure cap
- factor / regime exposure cap
- conviction band sizing
- max turnover budget
- explicit cash buffer policy

---

## Recommended redesign sequence

### Phase R1 — Freeze unsafe automation and document current semantics
**Goal:** Keep the system safe while redesign happens.

**Files likely to change:**
- `deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
- `packages/supervisor/orchestration/run_supervisor_cycle.py`
- `docs/operations/phase9-supervisor-orchestration-runbook.md`
- `docs/architecture/supervisor-conventions.md`

**Actions:**
- keep paper trading stopped
- add an explicit “scoring under redesign / not trusted for trading” flag in operator surfaces
- split recommendation generation from paper-portfolio execution in orchestration

### Phase R2 — Add durable feature + label store
**Goal:** Make the system measurable.

**Files likely to change:**
- Create: `packages/db/migrations/0009_feature_label_plane.sql`
- Create: `packages/supervisor/features/build_feature_snapshots.py`
- Create: `packages/supervisor/evaluation/build_forward_labels.py`
- Create: `packages/supervisor/evaluation/benchmarks.py`
- Create: `docs/operations/feature-label-plane-runbook.md`

**Outputs:**
- `feature_snapshots`
- `ticker_forward_outcomes`
- benchmark-relative labels

### Phase R3 — Replace family-score ranking with explicit scorecards
**Goal:** Separate alpha, quality, risk, and execution logic.

**Files likely to change:**
- Replace/retire: `packages/supervisor/signals/build_signals.py`
- Replace/retire: `packages/supervisor/signals/rank_candidates.py`
- Create: `packages/supervisor/scoring/build_alpha_scores.py`
- Create: `packages/supervisor/scoring/build_quality_scores.py`
- Create: `packages/supervisor/scoring/build_risk_scores.py`
- Create: `packages/supervisor/scoring/build_execution_scores.py`
- Create: `packages/supervisor/scoring/compose_decision_scores.py`
- Create: `packages/supervisor/scoring/common.py`
- Create: `packages/supervisor/scoring/policies.py`

**Outputs:**
- `alpha_scores`
- `quality_scores`
- `risk_scores`
- `execution_scores`
- `decision_scores`

### Phase R4 — Build real confidence and calibration framework
**Goal:** Turn confidence into something operators can trust.

**Files likely to change:**
- Replace: `packages/supervisor/reports/evaluate_recommendations.py`
- Replace: `packages/supervisor/reports/calibration.py`
- Create: `packages/supervisor/evaluation/calibration_curves.py`
- Create: `packages/supervisor/evaluation/scorecard_metrics.py`
- Create: `packages/supervisor/evaluation/cohort_analysis.py`
- Create: `packages/supervisor/evaluation/promotion_thresholds.py`
- Create: `docs/operations/scoring-calibration-runbook.md`

**Metrics to compute:**
- hit rate by decision-score decile
- avg forward return by decile
- max drawdown by decile
- regime-conditional performance
- sector-conditional performance
- liquidity-bucket performance
- calibration error / Brier-like metrics for directional outcomes
- sample size and confidence intervals

### Phase R5 — Redesign recommendation schema and API/UI surfaces
**Goal:** Show meaningful objects, not heuristic leftovers.

**Files likely to change:**
- Create: `packages/db/migrations/0010_recommendation_redesign.sql`
- Replace: `packages/supervisor/recommendations/generate_recommendations.py`
- Replace: `packages/supervisor/theses/generate_theses.py`
- Replace: `packages/supervisor/reports/generate_daily_brief.py`
- Modify: `apps/web/src/app/api/brain/recommendations/route.ts`
- Modify: `apps/web/src/app/api/brain/daily-brief/route.ts`
- Modify: `apps/web/src/app/app/recommendations/page.tsx`
- Modify: `apps/web/src/app/app/briefing/page.tsx`
- Create: `apps/web/src/components/recommendations/ScorecardPanel.tsx`
- Create: `apps/web/src/components/recommendations/CalibrationBadge.tsx`

**UI requirements:**
- show subscores separately
- show confidence types separately
- show expected return / risk estimates
- show sample size and calibration cohort
- show “not paper-eligible” reasons explicitly

### Phase R6 — Rebuild policy and paper trading as promotion stages
**Goal:** Make paper trading a proving ground, not an automatic downstream effect.

**Files likely to change:**
- Replace: `packages/supervisor/policy/engine.py`
- Replace: `packages/supervisor/portfolio/paper_order_engine.py`
- Create: `packages/supervisor/policy/promotion_engine.py`
- Create: `packages/supervisor/portfolio/constructor.py`
- Create: `packages/supervisor/portfolio/risk_budget.py`
- Create: `packages/supervisor/portfolio/cost_model.py`
- Modify: `packages/supervisor/orchestration/run_supervisor_cycle.py`

**Promotion requirements:**
- recommendation generation can run daily
- paper eligibility is separate
- paper portfolio can be disabled independently
- promotion thresholds are data-backed and versioned

### Phase R7 — Add score versioning and replayability
**Goal:** Make score changes auditable across versions.

**Files likely to change:**
- Create: `packages/db/migrations/0011_score_versioning.sql`
- Create: `packages/supervisor/scoring/registry.py`
- Create: `packages/supervisor/evaluation/replay_score_versions.py`
- Modify: existing replay / evaluation scripts

**Outputs:**
- `score_versions`
- `decision_policy_versions`
- `replay_comparisons`

This allows “v1 vs v2” comparisons before any re-enabling of paper trading.

---

## Concrete schema redesign

### Tables to add
- `feature_snapshots`
- `feature_definitions`
- `ticker_forward_outcomes`
- `benchmark_snapshots`
- `alpha_scores`
- `quality_scores`
- `risk_scores`
- `execution_scores`
- `decision_scores`
- `score_versions`
- `promotion_decisions`
- `calibration_runs`
- `calibration_buckets`
- `cohort_metrics`

### Tables to deprecate or narrow
- `candidate_rankings`
  - keep for backward compatibility at first
  - eventually replace with `decision_scores`
- `recommendation_outcomes`
  - replace simplistic sign-of-5d-return semantics with richer forward-outcome table

---

## Validation and trust requirements before re-enabling paper trading

Paper trading should remain disabled until all of the below are true.

### Statistical trust gates
- minimum N by decision cohort
- positive expected value in target buckets
- stable results across at least multiple recent cycles/windows
- no severe regime-specific blowups hidden by averages
- calibration surface materially better than current heuristic baseline

### System trust gates
- recommendation generation and paper eligibility are separate pipelines
- score version is stored on every recommendation
- promotion thresholds are stored and queryable
- operator UI shows why something is or is not paper-eligible

### Operational trust gates
- one command verifies latest score version, calibration run, promotion thresholds, and paper-trading disable state
- daily brief clearly labels whether ideas are research-only, watch, paper-eligible, or paper-active

---

## Immediate next implementation plan

### Task 1: Document current-score trust gaps in repo
**Files:**
- Create: `docs/architecture/vietmarket-scoring-trust-gaps.md`
- Modify: `docs/operations/phase9-supervisor-orchestration-runbook.md`
- Modify: `docs/operations/phase5-portfolio-policy-runbook.md`

### Task 2: Introduce a score-redesign architecture doc
**Files:**
- Create: `docs/architecture/vietmarket-scoring-v2.md`
- Create: `docs/architecture/vietmarket-confidence-semantics.md`
- Create: `docs/architecture/vietmarket-promotion-policy.md`

### Task 3: Add feature + forward-label migrations and builders
**Files:**
- Create: `packages/db/migrations/0009_feature_label_plane.sql`
- Create: `packages/supervisor/features/build_feature_snapshots.py`
- Create: `packages/supervisor/evaluation/build_forward_labels.py`
- Test: `tests/phaseR2_feature_label_plane_smoke.test.mjs`

### Task 4: Add evaluation notebooks/scripts for decile and regime analysis
**Files:**
- Create: `packages/supervisor/evaluation/analyze_score_deciles.py`
- Create: `packages/supervisor/evaluation/analyze_regime_stability.py`
- Create: `scripts/verify_scoring_redesign_baseline.sh`

### Task 5: Implement v2 score builders in parallel with current system
**Files:**
- Create: `packages/supervisor/scoring/*.py`
- Do not delete current Phase 3 files yet.
- Run both systems side-by-side until comparison evidence is strong.

### Task 6: Build score comparison UI
**Files:**
- Create: `apps/web/src/app/app/evaluation/scoring/page.tsx`
- Create: `apps/web/src/components/evaluation/ScoreVersionComparison.tsx`
- Create: `apps/web/src/app/api/brain/scoring-eval/route.ts`

### Task 7: Replace recommendation/promotion path only after evidence review
**Files:**
- Modify recommendation, policy, portfolio, orchestration layers after v2 outperforms baseline.

---

## Risks and tradeoffs

### Risk: overfitting to limited VN data history
Mitigation:
- use rolling windows
- compare by regime and liquidity bucket
- prefer robust simple models over clever unstable ones

### Risk: too much complexity too early
Mitigation:
- keep deterministic feature layer simple
- version policies explicitly
- build scorecards before fancy ML
- preserve side-by-side replay path

### Risk: false precision in UI
Mitigation:
- label confidence semantics clearly
- show sample size and cohort metadata
- display uncertainty bands where possible
- avoid naked scalar confidence without provenance

### Risk: operator confusion during migration
Mitigation:
- add explicit “legacy scoring” vs “v2 scoring” labels
- keep paper trading disabled until migration ends
- annotate briefing surfaces with score version

---

## Success criteria

The redesign is successful when:
- score math is separated into alpha / quality / risk / execution / decision layers
- confidence shown to operators is empirically grounded and labeled by type
- recommendations are generated from deterministic scored artifacts, not heuristic bucket prose
- paper trading is re-enabled only through an explicit promotion gate backed by evaluation evidence
- the operator can inspect any recommendation and answer:
  - what features drove it
  - what historical cohort supports it
  - what regime assumptions apply
  - what could invalidate it
  - why it is or is not paper-eligible

---

## Recommended first implementation slice

If you want me to execute this incrementally, the highest-leverage first slice is:

1. add the trust-gap docs
2. add forward-outcome labels + richer evaluation tables
3. build score-decile / calibration analysis
4. design v2 score schema
5. keep paper trading off until v2 evaluation is visible in app
