import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0012_scoring_v2.sql',
  'packages/supervisor/scoring/build_scores_v2.py',
  'packages/supervisor/scoring/common.py',
  'apps/web/src/app/api/brain/scoring-v2/route.ts',
  'scripts/verify_scoring_v2.sh',
  'docs/operations/scoring-v2-runbook.md',
];

test('scoring v2 files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('scoring v2 migration defines score tables', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0012_scoring_v2.sql'), 'utf8');
  for (const needle of ['score_versions', 'alpha_scores', 'quality_scores', 'risk_scores_v2', 'execution_scores', 'decision_scores']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('evaluation cycle runs scoring v2 builder', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  assert.match(script, /build_scores_v2\.py/);
});

test('scoring v2 API and evaluation route expose v2 artifacts', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/scoring-v2/route.ts'), 'utf8');
  const evalRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/evaluation/route.ts'), 'utf8');
  for (const needle of ['decision_scores', 'score_versions', 'alpha_score', 'decision_score']) {
    assert.match(route, new RegExp(needle));
    assert.match(evalRoute, new RegExp(needle));
  }
});

test('scoring v2 dashboard preview exists', () => {
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/evaluation/EvaluationDashboard.tsx'), 'utf8');
  assert.match(dashboard, /Scoring v2 preview/);
  assert.match(dashboard, /decision_scores_v2/);
});
