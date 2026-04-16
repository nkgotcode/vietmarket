import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('obsolete scoring-v2 endpoint and smoke test are removed after grade reset UI migration', () => {
  assert.equal(existsSync(path.join(repo, 'apps/web/src/app/api/brain/scoring-v2/route.ts')), false);
  assert.equal(existsSync(path.join(repo, 'tests/phase11_scoring_v2_smoke.test.mjs')), false);
});

test('evaluation API and dashboard now use grade-plane preview semantics', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/evaluation/route.ts'), 'utf8');
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/evaluation/EvaluationDashboard.tsx'), 'utf8');
  for (const needle of ['decision_states_v2', 'Opportunity Grade', 'Forecast Reliability', 'grade_preview']) {
    assert.match(route + '\n' + dashboard, new RegExp(needle));
  }
  assert.doesNotMatch(dashboard, /Scoring v2 preview/);
  assert.doesNotMatch(route, /decision_scores_v2/);
});
