import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('promotion gate reads decision_states_v2 and separates analytical state from admission status', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/policy/promotion_gate.py'), 'utf8');
  for (const needle of ['decision_states_v2', 'analytical_state', 'final_state', 'policy_blocked', 'admission_status']) {
    assert.match(script, new RegExp(needle));
  }
});

test('paper portfolio still depends only on admitted rows, not analytical state alone', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/portfolio/paper_order_engine.py'), 'utf8');
  assert.match(script, /FROM paper_trade_admissions/);
  assert.match(script, /admission_status != 'admitted'/);
  assert.doesNotMatch(script, /analytical_state == 'paper_eligible'/);
});

test('policy engine reads decision-state separation instead of only old scoring semantics', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/policy/engine.py'), 'utf8');
  for (const needle of ['decision_states_v2', 'policy_blocked', 'analytical_state']) {
    assert.match(script, new RegExp(needle));
  }
});
