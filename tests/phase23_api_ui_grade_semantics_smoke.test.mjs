import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('recommendations API reads grade-plane decision semantics', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/recommendations/route.ts'), 'utf8');
  for (const needle of ['decision_states_v2', 'analytical_state', 'final_state', 'policy_blocked', 'state_json']) {
    assert.match(route, new RegExp(needle));
  }
});

test('recommendations UI presents labeled grade semantics instead of naked old confidence terms', () => {
  const card = readFileSync(path.join(repo, 'apps/web/src/components/recommendations/RecommendationCard.tsx'), 'utf8');
  for (const needle of ['Opportunity Grade', 'Evidence Grade', 'Tradability Grade', 'Risk Containment Grade', 'Forecast Reliability', 'Evidence Reliability', 'Execution Reliability']) {
    assert.match(card, new RegExp(needle));
  }
  assert.doesNotMatch(card, />model /);
  assert.doesNotMatch(card, />Decision /);
});

test('operator control API and dashboard expose analytical_state and policy_blocked separation', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/operator-control/route.ts'), 'utf8');
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/operator/OperatorControlDashboard.tsx'), 'utf8');
  for (const needle of ['analytical_state', 'policy_blocked', 'Opportunity Grade', 'Execution Reliability']) {
    assert.match(route + '\n' + dashboard, new RegExp(needle));
  }
});
