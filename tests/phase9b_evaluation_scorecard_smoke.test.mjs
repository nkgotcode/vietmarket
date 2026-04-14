import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/supervisor/reports/run_evaluation_cycle.py',
  'apps/web/src/app/api/brain/evaluation/route.ts',
  'apps/web/src/app/app/evaluation/page.tsx',
  'apps/web/src/components/evaluation/EvaluationDashboard.tsx',
  'scripts/verify_phase9b_evaluation_scorecard.sh',
  'docs/operations/phase9b-evaluation-scorecard-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-9b-evaluation-scorecard-execution.md',
];

test('Phase 9B required files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 9B evaluation runner executes existing phase7 scripts', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  for (const needle of ['evaluate_recommendations.py', 'run_replay.py', 'calibration.py', 'worker_run']) {
    assert.match(script, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('Phase 9B evaluation API reads evaluation and portfolio artifacts', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/evaluation/route.ts'), 'utf8');
  for (const needle of ['recommendation_outcomes', 'replay_runs', 'replay_results', 'calibration_metrics', 'prompt_versions', 'model_runs', 'portfolio_snapshots', 'supervisor_runs']) {
    assert.match(route, new RegExp(needle));
  }
});

test('Phase 9B app home links to evaluation page', () => {
  const page = readFileSync(path.join(repo, 'apps/web/src/app/app/page.tsx'), 'utf8');
  assert.match(page, /\/app\/evaluation/);
});

test('Phase 9B verify script runs evaluation cycle', () => {
  const verify = readFileSync(path.join(repo, 'scripts/verify_phase9b_evaluation_scorecard.sh'), 'utf8');
  assert.match(verify, /run_evaluation_cycle\.py/);
  assert.match(verify, /recommendation_outcomes/);
  assert.match(verify, /calibration_metrics/);
});
