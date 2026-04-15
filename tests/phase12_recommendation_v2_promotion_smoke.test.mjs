import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('recommendation generation consumes decision_scores and explicit promotion states', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/recommendations/generate_recommendations.py'), 'utf8');
  for (const needle of ['JOIN decision_scores', 'recommended_state', 'paper_eligible', 'decision_score', 'score_version']) {
    assert.match(script, new RegExp(needle));
  }
});

test('recommendation API exposes scoring v2 fields', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/recommendations/route.ts'), 'utf8');
  for (const needle of ['recommendation_scorecards', 'promotion_decisions', 'alpha_score', 'quality_score', 'risk_score', 'execution_score', 'recommended_state', 'paper_eligible']) {
    assert.match(route, new RegExp(needle));
  }
});

test('recommendation UI shows scoring v2 semantics', () => {
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/recommendations/RecommendationsDashboard.tsx'), 'utf8');
  const card = readFileSync(path.join(repo, 'apps/web/src/components/recommendations/RecommendationCard.tsx'), 'utf8');
  assert.match(dashboard, /promotion semantics/i);
  for (const needle of ['Decision', 'Alpha', 'Quality', 'Risk', 'Exec', 'paper_eligible']) {
    assert.match(card, new RegExp(needle));
  }
});

test('daily and intraday brief builders use recommendation or decision v2 fields', () => {
  const daily = readFileSync(path.join(repo, 'packages/supervisor/reports/generate_daily_brief.py'), 'utf8');
  const intraday = readFileSync(path.join(repo, 'packages/supervisor/reports/generate_intraday_brief.py'), 'utf8');
  for (const needle of ['decision_score', 'paper_eligible', 'score_version']) {
    assert.match(daily, new RegExp(needle));
  }
  for (const needle of ['FROM decision_scores', 'recommended_state', 'paper_eligible']) {
    assert.match(intraday, new RegExp(needle));
  }
});

test('policy engine accepts explicit promotion states', () => {
  const checks = readFileSync(path.join(repo, 'packages/supervisor/policy/checks.py'), 'utf8');
  const engine = readFileSync(path.join(repo, 'packages/supervisor/policy/engine.py'), 'utf8');
  for (const needle of ['paper_eligible', 'candidate', 'watch']) {
    assert.match(checks, new RegExp(needle));
  }
  for (const needle of ['decision_scores', 'paper_eligible', 'decision_score']) {
    assert.match(engine, new RegExp(needle));
  }
});
