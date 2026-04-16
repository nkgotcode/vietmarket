# VietMarket Grading System Reset Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace VietMarket’s current heuristic score/confidence/liquidity grading stack with a clearer, auditable, outcome-linked grading system whose numbers mean one thing each and can be defended to an operator.

**Architecture:** Move from a blended heuristic scoring pipeline to a layered grading architecture: deterministic feature plane, explicit grade dimensions, empirical reliability plane, execution-capacity plane, and policy/admission plane. The new system should separate descriptive facts, predictive edge, data reliability, execution feasibility, and actionability instead of collapsing them into a few overloaded numbers.

**Tech Stack:** Timescale/Postgres, Python supervisor workers, SQL-backed evaluation artifacts, Next.js operator surfaces, Nomad periodic jobs, repo-native verification scripts, Hermes only for narrative explanation after deterministic scoring.

---

## I'm using the writing-plans skill to create the implementation plan.

## Why a full reset is justified

The current v2 system is already cleaner than legacy Phase 3, but it still has structural problems that make operator trust hard:

1. **`model_confidence` is not actually “confidence” in the operator sense**
   - Current code mixes calibration strength, legacy confidence, alpha score, and regime confidence into one number.
   - File: `packages/supervisor/scoring/build_scores_v2.py`
   - This is better than the old heuristic, but it still conflates:
     - model quality,
     - setup strength,
     - regime certainty,
     - legacy carry-over.

2. **`execution_score` is being reused as the policy liquidity gate**
   - Policy maps `liquidity_score = execution_score / 100.0`.
   - File: `packages/supervisor/policy/engine.py`
   - That means “liquidity” is not a first-class measure; it is just a renamed execution proxy.

3. **The system still leans on legacy scores/confidences in places that should have been reset entirely**
   - `legacy_total_score`
   - `legacy_total_confidence`
   - `legacy_bucket`
   - `legacy_blocking_flag`
   - File: `packages/supervisor/scoring/common.py`
   - This prevents a true semantic reset.

4. **Grades are still too tightly coupled to gating**
   - The same family of numbers is used to explain, rank, and block.
   - This makes it hard to tell whether a name is:
     - a weak signal,
     - a good signal with bad data,
     - a good signal but untradeable,
     - a good signal that policy correctly blocks.

5. **The operator cannot cleanly answer: “what does this number mean?”**
   - Every visible number should have one sentence of meaning.
   - Right now that standard is not met.

---

## Design principles for the reset

### Principle 1: One number, one meaning
A grade must have exactly one job.

Bad:
- a score that partly means predictive edge and partly means data quality
- a confidence number that partly means calibration and partly means freshness
- a liquidity number that is really an execution score alias

Good:
- one grade for predictive edge
- one grade for evidence reliability
- one grade for execution feasibility
- one grade for downside fragility
- one explicit action/admission decision layer

### Principle 2: Separate facts from judgments
The stack should flow like this:
- raw market / company / news facts
- deterministic derived features
- model estimates / rankings
- reliability grades
- execution feasibility grades
- policy decision
- paper-trade admission

No later layer should overwrite the meaning of an earlier one.

### Principle 3: Grades must be operator-native, not model-native
The output should answer operator questions directly:
- Is this setup statistically attractive?
- Are the inputs trustworthy?
- Can this actually be traded cleanly?
- Is downside asymmetry acceptable?
- Is the system allowing it right now?

### Principle 4: Policy should never masquerade as analysis
A blocked name can still be analytically strong.
The operator should be able to see:
- strong thesis / edge
- weak evidence
- poor execution
- policy block

as separate truths.

### Principle 5: Eliminate semantic dependence on legacy score fields
Legacy Phase 3 / early v2 artifacts can be kept for migration and comparison only.
They must not remain part of the authoritative grade formulas.

---

## Proposed replacement architecture

## Layer 0 — Canonical Facts Plane
Persist source-of-truth, non-judgmental facts.

Examples:
- price, volume, turnover, volatility
- financial statement timestamps and freshness
- sector / exchange / float metadata
- article counts, event flags, corporate action flags
- benchmark and sector returns
- market regime snapshot
- breadth / liquidity environment state

Likely files:
- `packages/supervisor/snapshots/build_market_state.py`
- `packages/supervisor/snapshots/ticker_snapshot_builder.py`
- `packages/supervisor/signals/common.py`

Potential schema additions:
- `feature_snapshots`
- `feature_sources`
- `feature_quality_events`

## Layer 1 — Feature Plane
Convert facts into deterministic model inputs.

Feature families:
- trend continuation / reversal features
- momentum persistence features
- event / catalyst features
- fundamentals quality and freshness features
- liquidity / turnover / tradability features
- downside risk / stability features
- sector-relative and market-relative features
- regime interaction features

Rules:
- features must be persisted independently from grades
- each feature should have lineage and documentation
- feature missingness should itself become a first-class signal in the reliability plane

## Layer 2 — Estimate Plane
This layer predicts or estimates economic properties, not policy outcomes.

Replace the current broad score family with explicit estimated quantities:

1. **edge_estimate**
   - expected directional edge over horizon
   - should be rankable cross-sectionally
   - replaces today’s overloaded “alpha_score” semantics with a more explicit label

2. **downside_estimate**
   - expected fragility / drawdown / instability risk
   - should be economic, not just cosmetic

3. **execution_cost_estimate**
   - expected implementation friction / slippage / capacity stress
   - should not be encoded as a generic score first

4. **data_reliability_estimate**
   - expected trustworthiness of the underlying input set
   - based on missingness, recency, source health, and regime coverage

Each estimate should be stored in raw-ish units or well-defined normalized form before any letter/number grade is assigned.

## Layer 3 — Grade Plane
This is the operator-visible grading system.

### Replace raw overloaded scores with 4 primary grades

#### A. Opportunity Grade
Question answered:
- “How attractive is the setup if we ignore execution/policy for a moment?”

Inputs:
- edge_estimate
- regime-relative performance expectation
- benchmark-relative expectation
- sector-relative strength context

Output examples:
- letter: `A`, `B`, `C`, `D`, `F`
- numeric companion: `opportunity_percentile`

#### B. Evidence Grade
Question answered:
- “How much should we trust the inputs behind this setup?”

Inputs:
- feature completeness
- financial recency
- ingest health
- missing critical fields
- event/news coverage sufficiency
- sample size for comparable historical bucket

Output examples:
- `strong`, `good`, `thin`, `fragile`, `invalid`
- companion numeric reliability index

#### C. Tradability Grade
Question answered:
- “Could we realistically act on this without bad implementation quality?”

Inputs:
- turnover
- volume
- liquidity bucket
- likely slippage proxy
- event distortion risk
- capacity constraints

Output examples:
- `excellent`, `good`, `borderline`, `poor`, `untradeable`

#### D. Risk Containment Grade
Question answered:
- “How controllable is the downside profile if we are wrong?”

Inputs:
- realized volatility
- adverse excursion history
- regime instability
- event risk
- health flags
- corporate action proximity

Output examples:
- `contained`, `acceptable`, `fragile`, `hazardous`

### Important rule
These four grades must be displayed together.
No single replacement “master confidence” should appear above them.

## Layer 4 — Reliability Plane
Instead of one confidence number, define explicit reliability outputs:

1. **Forecast Reliability**
   - historical reliability of similar opportunity buckets in similar regimes

2. **Evidence Reliability**
   - completeness and freshness of the data used

3. **Execution Reliability**
   - likelihood that implementation quality is acceptable

These may remain numeric internally, but UI labels must be explicit.
Examples:
- `forecast_reliability = 0.61`
- `evidence_reliability = 0.82`
- `execution_reliability = 0.34`

And in the UI they should render as labeled chips, not a single generic “confidence”.

## Layer 5 — Decision Plane
Once the four grades and three reliability dimensions exist, derive action states.

Recommended states:
- `invalid`
- `research_only`
- `watch`
- `candidate`
- `paper_eligible`
- `portfolio_candidate`
- `blocked`
- `retired`

State derivation rules should depend on explicit combinations, for example:
- strong opportunity + thin evidence -> `watch`
- strong opportunity + poor tradability -> `watch` or `blocked_execution`
- medium opportunity + strong evidence + good tradability -> `candidate`
- strong opportunity + strong evidence + good tradability + acceptable risk -> `paper_eligible`

### Critical change
Do not let raw grades directly imply portfolio admission.
There must still be a separate promotion gate.

## Layer 6 — Admission Plane
This is where policy acts.

Inputs:
- decision state
- current system health
- current market regime policy
- portfolio concentration constraints
- capital/capacity rules
- promotion policy version

Outputs:
- `admission_status`
- `admission_reason`
- `admission_priority`

This plane should continue to own:
- paper-trading enabled/disabled
- max new positions
- sector limits
- portfolio sizing permissions

---

## Replacement schema proposal

### New tables
- `grade_versions`
- `feature_snapshots`
- `estimate_snapshots`
- `opportunity_grades`
- `evidence_grades`
- `tradability_grades`
- `risk_containment_grades`
- `reliability_snapshots`
- `decision_states_v2`
- `promotion_admissions_v2`
- `grade_calibration_runs`
- `grade_bucket_metrics`

### Tables to deprecate from authoritative path
Keep temporarily for migration and comparisons only:
- `alpha_scores`
- `quality_scores`
- `risk_scores_v2`
- `execution_scores`
- `decision_scores`

### Existing tables likely to remain but change meaning
- `recommendations`
- `recommendation_scorecards`
- `promotion_decisions`
- `policy_results`

---

## Formula reset proposal

### Remove these dependencies from authoritative grading
- `legacy_total_score`
- `legacy_total_confidence`
- `legacy_bucket`
- `legacy_blocking_flag`

### Replace current confidence formulas with reliability-specific formulas

#### Forecast Reliability
Should depend on:
- historical calibration of comparable bucket
- regime-conditioned hit rate
- confidence interval width
- comparable sample size

#### Evidence Reliability
Should depend on:
- missing critical features count
- financial recency bands
- source health/degradation state
- stale or missing event coverage

#### Execution Reliability
Should depend on:
- turnover percentile
- capacity percentile
- slippage proxy percentile
- event distortion risk

### Replace policy `liquidity_score` with `tradability_index`
Current system:
- `liquidity_score = execution_score / 100`

New system:
- compute `tradability_index` directly
- keep `execution_cost_estimate` separately
- keep `capacity_band` separately
- let policy gate on explicit tradability thresholds, not a renamed execution score

---

## Operator-facing UI redesign

### Recommendations page should show
For each ticker:
- Opportunity Grade
- Evidence Grade
- Tradability Grade
- Risk Containment Grade
- Forecast Reliability
- Evidence Reliability
- Execution Reliability
- Decision State
- Admission Status
- Block reason / caution reason

### Prohibited UI patterns
- one unlabeled “confidence” pill
- one unlabeled “liquidity” pill if it is actually execution-derived
- one dominant master score with tiny explanation text below it

### Desired explanation pattern
For each ticker:
- **Why it surfaced**
- **Why the data is or isn’t trustworthy**
- **Why trading it would or wouldn’t be feasible**
- **Why policy currently allows or blocks it**

Likely files:
- `apps/web/src/components/recommendations/RecommendationsDashboard.tsx`
- `apps/web/src/components/recommendations/RecommendationCard.tsx`
- `apps/web/src/app/api/brain/recommendations/route.ts`
- `apps/web/src/app/api/brain/scoring-v2/route.ts`

---

## Migration strategy

### Phase 1: Define semantics and versioning
Goal:
- introduce the new grade vocabulary without changing live behavior yet

Deliverables:
- grade glossary doc
- `grade_versions` table
- config JSON for authoritative grade definitions
- UI labels and terminology spec

### Phase 2: Persist feature and estimate layers
Goal:
- decouple raw facts/features from grades

Deliverables:
- feature snapshot persistence
- estimate snapshot persistence
- lineage metadata
- deterministic test fixtures

### Phase 3: Implement new grade builders side-by-side
Goal:
- compute the four primary grades and three reliability measures in parallel with current v2

Deliverables:
- new builder modules
- new DB tables
- preview API route
- comparison dashboard vs current v2

### Phase 4: Rebuild decision state logic on top of the new grades
Goal:
- derive `watch/candidate/paper_eligible/...` from the new state model

Deliverables:
- new decision-state worker
- new explanation payloads
- updated recommendation writer

### Phase 5: Rebuild policy/admission rules
Goal:
- move policy to explicit admission semantics using new grades

Deliverables:
- new promotion/admission thresholds
- migration from current `promotion_decisions` semantics
- updated paper portfolio gate

### Phase 6: Switch UI and APIs to new grading system
Goal:
- operator sees only the new semantics by default

Deliverables:
- new API contracts
- UI chips/cards/tables
- backward-compatible fallback during rollout

### Phase 7: De-authorize old grades
Goal:
- keep old tables only for audit/backtest comparison

Deliverables:
- remove old tables from active decision path
- mark old artifacts deprecated in code/docs
- final migration note

---

## Files likely to change

### Migrations
- Create: `packages/db/migrations/0015_grading_reset_foundation.sql`
- Create: `packages/db/migrations/0016_grade_plane_tables.sql`
- Create: `packages/db/migrations/0017_decision_state_reset.sql`

### Scoring / grading workers
- Create: `packages/supervisor/grading/common.py`
- Create: `packages/supervisor/grading/build_feature_snapshots.py`
- Create: `packages/supervisor/grading/build_estimates.py`
- Create: `packages/supervisor/grading/build_grades.py`
- Create: `packages/supervisor/grading/build_decision_states.py`
- Create: `packages/supervisor/grading/calibrate_grades.py`
- Deprecate/bridge: `packages/supervisor/scoring/build_scores_v2.py`
- Deprecate/bridge: `packages/supervisor/scoring/common.py`

### Policy / admission
- Modify: `packages/supervisor/policy/engine.py`
- Modify: `packages/supervisor/policy/checks.py`
- Modify: `packages/supervisor/policy/default_rules.py`
- Modify: `packages/supervisor/policy/promotion_gate.py`
- Modify: `packages/supervisor/portfolio/paper_order_engine.py`

### Recommendation layer
- Modify: `packages/supervisor/recommendations/generate_recommendations.py`
- Modify: `packages/supervisor/reports/generate_daily_brief.py`
- Modify: `packages/supervisor/reports/generate_intraday_brief.py`

### Operator APIs/UI
- Modify: `apps/web/src/app/api/brain/recommendations/route.ts`
- Modify: `apps/web/src/app/api/brain/scoring-v2/route.ts`
- Create: `apps/web/src/app/api/brain/grades/route.ts`
- Modify: `apps/web/src/components/recommendations/RecommendationsDashboard.tsx`
- Modify: `apps/web/src/components/recommendations/RecommendationCard.tsx`
- Create: `apps/web/src/components/recommendations/GradeBreakdownCard.tsx`

### Docs / runbooks
- Modify: `docs/operations/scoring-v2-runbook.md`
- Create: `docs/operations/grading-reset-runbook.md`
- Create: `docs/operations/grade-semantics-reference.md`

### Tests
- Create: `tests/phase15_grading_reset_foundation_smoke.test.mjs`
- Create: `tests/phase16_grade_plane_smoke.test.mjs`
- Create: `tests/phase17_decision_state_reset_smoke.test.mjs`
- Modify: existing phase 11-14 tests to support transition behavior

---

## Task breakdown

### Task 1: Write the semantics spec before changing arithmetic

**Files:**
- Create: `docs/operations/grade-semantics-reference.md`
- Modify: `docs/plans/2026-04-16-vietmarket-grading-system-reset.md`

**Step 1: Write the failing spec checklist**
Define required properties:
- every grade has one meaning
- no authoritative dependency on legacy total score/confidence
- no unlabeled confidence in UI
- policy block is distinct from analytical strength

**Step 2: Review against current code**
Inspect:
- `packages/supervisor/scoring/build_scores_v2.py`
- `packages/supervisor/policy/engine.py`
- `packages/supervisor/recommendations/generate_recommendations.py`

**Step 3: Write the semantics reference**
Include:
- grade glossary
- reliability glossary
- state glossary
- deprecated terminology list

**Step 4: Verify**
Manual review: confirm each visible grade name maps to exactly one definition.

**Step 5: Commit**
`git commit -m "docs: define grading reset semantics"`

### Task 2: Add grade versioning and new grade-plane tables

**Files:**
- Create: `packages/db/migrations/0015_grading_reset_foundation.sql`
- Test: `tests/phase15_grading_reset_foundation_smoke.test.mjs`

**Step 1: Write the failing migration smoke test**
Assert presence of:
- `grade_versions`
- `estimate_snapshots`
- `opportunity_grades`
- `evidence_grades`
- `tradability_grades`
- `risk_containment_grades`
- `reliability_snapshots`

**Step 2: Run the test and verify failure**
Run:
`node --test tests/phase15_grading_reset_foundation_smoke.test.mjs`

**Step 3: Implement minimal migration**
Add tables + core indexes.

**Step 4: Re-run the test**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: add grading reset foundation tables"`

### Task 3: Persist feature and estimate layers separately

**Files:**
- Create: `packages/supervisor/grading/common.py`
- Create: `packages/supervisor/grading/build_feature_snapshots.py`
- Create: `packages/supervisor/grading/build_estimates.py`
- Test: `tests/phase16_grade_plane_smoke.test.mjs`

**Step 1: Write failing tests for outputs and schema assumptions**
Verify:
- estimate builder does not depend on legacy score fields for authoritative outputs
- feature outputs are persisted independently

**Step 2: Run the tests and capture failure**

**Step 3: Implement minimal feature and estimate writers**
Persist:
- feature inputs
- edge estimate
- downside estimate
- execution cost estimate
- data reliability estimate

**Step 4: Re-run tests**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: persist grade features and estimates"`

### Task 4: Build the new grades and reliability outputs side-by-side

**Files:**
- Create: `packages/supervisor/grading/build_grades.py`
- Create: `packages/supervisor/grading/calibrate_grades.py`
- Modify: `packages/supervisor/reports/run_evaluation_cycle.py`
- Test: `tests/phase16_grade_plane_smoke.test.mjs`

**Step 1: Write failing tests for grade outputs**
Assert generation of:
- opportunity grade
- evidence grade
- tradability grade
- risk containment grade
- forecast/evidence/execution reliability

**Step 2: Run tests and verify failure**

**Step 3: Implement minimal grade builder**
Use versioned config and explicit formulas.

**Step 4: Re-run tests**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: add side-by-side grading plane"`

### Task 5: Rebuild decision states on top of grades

**Files:**
- Create: `packages/supervisor/grading/build_decision_states.py`
- Modify: `packages/supervisor/recommendations/generate_recommendations.py`
- Modify: `packages/supervisor/policy/engine.py`
- Test: `tests/phase17_decision_state_reset_smoke.test.mjs`

**Step 1: Write failing tests**
Assert that:
- analytical strength can coexist with policy block
- weak evidence downgrades state without pretending the opportunity is weak
- poor tradability blocks execution without erasing opportunity grade

**Step 2: Run tests and verify failure**

**Step 3: Implement minimal state derivation**
Generate new states and explanation payloads.

**Step 4: Re-run tests**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: rebuild recommendation states on grade plane"`

### Task 6: Move policy to admission-only semantics

**Files:**
- Modify: `packages/supervisor/policy/checks.py`
- Modify: `packages/supervisor/policy/default_rules.py`
- Modify: `packages/supervisor/policy/promotion_gate.py`
- Modify: `packages/supervisor/portfolio/paper_order_engine.py`

**Step 1: Write failing tests for admission behavior**
Assert that:
- policy only controls admission
- analysis remains visible even when admission is denied
- `paper_trading_enabled = false` still prevents paper orders

**Step 2: Run tests and verify failure**

**Step 3: Implement minimal admission rewrite**
Separate:
- analysis state
- policy/admission state
- portfolio action state

**Step 4: Re-run tests**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: separate policy admission from analytical grading"`

### Task 7: Replace operator UI/API semantics

**Files:**
- Create: `apps/web/src/app/api/brain/grades/route.ts`
- Modify: `apps/web/src/app/api/brain/recommendations/route.ts`
- Modify: `apps/web/src/components/recommendations/RecommendationsDashboard.tsx`
- Modify: `apps/web/src/components/recommendations/RecommendationCard.tsx`
- Create: `apps/web/src/components/recommendations/GradeBreakdownCard.tsx`

**Step 1: Write failing UI/API tests or contract checks**
Assert:
- no naked `confidence`
- no naked `liquidity_score`
- labeled grade/reliability outputs appear in payloads

**Step 2: Run tests and verify failure**

**Step 3: Implement minimal API/UI migration**
Render the new breakdown cleanly.

**Step 4: Re-run tests**
Expected: PASS.

**Step 5: Commit**
`git commit -m "feat: expose grading reset semantics in UI and APIs"`

### Task 8: Validate, compare, and de-authorize the old path

**Files:**
- Modify: `docs/operations/grading-reset-runbook.md`
- Modify: verification scripts as needed
- Modify: comparison dashboard or ops script

**Step 1: Add comparison queries/scripts**
Compare old vs new states for latest cycles.

**Step 2: Run validation**
- `python3 -m py_compile packages/supervisor/**/*.py`
- `node --test tests/phase15_grading_reset_foundation_smoke.test.mjs`
- `node --test tests/phase16_grade_plane_smoke.test.mjs`
- `node --test tests/phase17_decision_state_reset_smoke.test.mjs`
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`

**Step 3: If writable primary is available, run live verification**
Verify:
- grade tables fill
- recommendations reflect new semantics
- policy/admission rows separate analytical vs operational truth

**Step 4: Mark old path deprecated**
Document which tables/fields are compatibility-only.

**Step 5: Commit**
`git commit -m "chore: validate grading reset and deprecate old path"`

---

## Validation requirements

### Unit / smoke
- schema smoke tests for new grade tables
- builder smoke tests for feature/estimate/grade/state outputs
- policy gate smoke tests for admission separation
- API contract tests for labeled outputs

### Build validation
- `python3 -m py_compile` on changed Python modules
- `node --test` on phase 15/16/17 tests
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`

### Live validation
Only after writable primary confirmation:
- run grade builders on latest cycle
- inspect output rows in new grade tables
- verify operator API payloads
- verify blocked names still display strong analysis when appropriate
- verify no paper orders are produced unless admission explicitly says so

---

## Risks and tradeoffs

1. **Bigger semantic change than a simple refactor**
   - This is not a rename pass.
   - It changes meaning, storage, UI, and policy boundaries.

2. **Migration complexity**
   - Existing dashboards and scripts likely assume `decision_score`, `confidence`, and `liquidity_score` semantics.

3. **Backtest/evaluation work may dominate effort**
   - If reliability is to be empirical, evaluation tables and calibration jobs must stay healthy.

4. **Operator confusion during rollout**
   - Old and new numbers may coexist for a time.
   - UI must label “legacy” vs “grade reset” clearly.

5. **Write-path dependency on DB target health**
   - Live verification still depends on a writable primary PG target.

---

## Open questions to resolve during implementation

1. Should operator-visible grades be:
   - letter grades,
   - labeled bands,
   - or labeled bands plus hidden numerics?

2. Should `opportunity grade` optimize:
   - expected raw return,
   - benchmark-relative excess return,
   - or a utility-adjusted expected value?

3. Should tradability incorporate a spread proxy now, or only turnover/volume/capacity until spread data exists?

4. Should reliability be rendered as:
   - percentages,
   - named levels,
   - or both?

5. What is the minimum side-by-side comparison period before de-authorizing old v2 outputs?

---

## Recommended immediate next move
Implement **Task 1 + Task 2 first**:
- freeze new semantics in docs
- create the new grade-plane tables and versioning

Do **not** begin by tweaking the current formulas again. That would just create “v2.1 heuristic drift” instead of a real grading reset.
