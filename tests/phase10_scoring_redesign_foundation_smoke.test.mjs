import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0011_scoring_evaluation_foundation.sql',
  'packages/supervisor/evaluation/build_forward_labels.py',
  'packages/supervisor/evaluation/analyze_score_deciles.py',
  'packages/supervisor/evaluation/analyze_regime_stability.py',
  'docs/architecture/vietmarket-scoring-trust-gaps.md',
  'docs/architecture/vietmarket-confidence-semantics.md',
  'docs/architecture/vietmarket-promotion-policy.md',
  'scripts/verify_scoring_redesign_baseline.sh',
];

test('scoring redesign foundation required files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('migration adds forward outcomes and calibration tables', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0011_scoring_evaluation_foundation.sql'), 'utf8');
  for (const needle of ['ticker_forward_outcomes', 'calibration_runs', 'calibration_buckets', 'cohort_metrics']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('evaluation cycle includes forward labels and cohort analysis', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  for (const needle of ['build_forward_labels.py', 'analyze_score_deciles.py', 'analyze_regime_stability.py', 'evaluate_recommendations.py', 'run_replay.py', 'calibration.py']) {
    assert.match(script, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('evaluation API exposes new scoring-eval artifacts', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/evaluation/route.ts'), 'utf8');
  for (const needle of ['ticker_forward_outcomes', 'calibration_runs', 'calibration_buckets', 'cohort_metrics', 'labels_coverage', 'calibration_run']) {
    assert.match(route, new RegExp(needle));
  }
});

test('baseline verify script inspects new evaluation artifacts', () => {
  const verify = readFileSync(path.join(repo, 'scripts/verify_scoring_redesign_baseline.sh'), 'utf8');
  for (const needle of ['run_evaluation_cycle.py', 'ticker_forward_outcomes', 'calibration_buckets', 'cohort_metrics']) {
    assert.match(verify, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});
