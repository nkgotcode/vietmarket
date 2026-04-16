import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0016_grading_feature_estimates.sql',
  'packages/supervisor/grading/common.py',
  'packages/supervisor/grading/build_feature_snapshots.py',
  'packages/supervisor/grading/build_estimates.py',
];

test('grading feature/estimate files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('grading feature/estimate migration defines feature snapshots table', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0016_grading_feature_estimates.sql'), 'utf8');
  for (const needle of ['feature_snapshots', 'feature_json', 'feature_quality_json']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('evaluation cycle runs grading feature and estimate builders', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  assert.match(script, /build_feature_snapshots\.py/);
  assert.match(script, /build_estimates\.py/);
});

test('grading estimate builder does not authoritatively depend on legacy score fields', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/grading/build_estimates.py'), 'utf8');
  assert.doesNotMatch(script, /legacy_total_score/);
  assert.doesNotMatch(script, /legacy_total_confidence/);
  assert.match(script, /edge_estimate/);
  assert.match(script, /execution_cost_estimate/);
  assert.match(script, /data_reliability_estimate/);
});
