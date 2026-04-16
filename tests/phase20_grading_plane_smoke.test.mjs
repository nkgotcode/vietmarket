import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/supervisor/grading/build_grades.py',
  'packages/supervisor/grading/calibrate_grades.py',
];

test('grading plane builder files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('evaluation cycle runs grade calibration and grade builders', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  assert.match(script, /calibrate_grades\.py/);
  assert.match(script, /build_grades\.py/);
});

test('grading builder persists all primary grades and reliability outputs', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/grading/build_grades.py'), 'utf8');
  for (const needle of [
    'opportunity_grades',
    'evidence_grades',
    'tradability_grades',
    'risk_containment_grades',
    'reliability_snapshots',
    'forecast_reliability',
    'evidence_reliability',
    'execution_reliability',
    'Opportunity Grade',
    'Evidence Grade',
    'Tradability Grade',
    'Risk Containment Grade',
  ]) {
    assert.match(script, new RegExp(needle));
  }
});

test('grading calibration builder reads estimate snapshots instead of legacy scoring fields', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/grading/calibrate_grades.py'), 'utf8');
  assert.match(script, /estimate_snapshots/);
  assert.doesNotMatch(script, /legacy_total_score/);
  assert.doesNotMatch(script, /legacy_total_confidence/);
});
