import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0017_decision_state_reset.sql',
  'packages/supervisor/grading/build_decision_states.py',
];

test('decision-state reset files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('decision-state migration defines decision_states_v2 table', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0017_decision_state_reset.sql'), 'utf8');
  for (const needle of ['decision_states_v2', 'analytical_state', 'policy_blocked', 'state_json']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('evaluation cycle runs decision-state builder', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/reports/run_evaluation_cycle.py'), 'utf8');
  assert.match(script, /build_decision_states\.py/);
});

test('recommendation layer reads new decision-state semantics', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/recommendations/generate_recommendations.py'), 'utf8');
  for (const needle of ['decision_states_v2', 'analytical_state', 'Opportunity Grade', 'Tradability Grade', 'policy_blocked']) {
    assert.match(script, new RegExp(needle));
  }
});
