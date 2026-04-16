import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

const files = [
  'packages/db/migrations/0015_grading_reset_foundation.sql',
  'docs/operations/grade-semantics-reference.md',
];

test('grading reset foundation files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('grading reset migration defines grade-plane foundation tables', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0015_grading_reset_foundation.sql'), 'utf8');
  for (const needle of [
    'grade_versions',
    'estimate_snapshots',
    'opportunity_grades',
    'evidence_grades',
    'tradability_grades',
    'risk_containment_grades',
    'reliability_snapshots',
  ]) {
    assert.match(migration, new RegExp(needle));
  }
});

test('grade semantics reference deprecates overloaded confidence and liquidity terms', () => {
  const doc = readFileSync(path.join(repo, 'docs/operations/grade-semantics-reference.md'), 'utf8');
  for (const needle of [
    'Opportunity Grade',
    'Evidence Grade',
    'Tradability Grade',
    'Risk Containment Grade',
    'Forecast Reliability',
    'Evidence Reliability',
    'Execution Reliability',
    'Deprecated terminology',
    'confidence',
    'liquidity_score',
  ]) {
    assert.match(doc, new RegExp(needle));
  }
});
