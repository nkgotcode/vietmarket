import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('promotion policy gate files exist', () => {
  for (const file of [
    'packages/db/migrations/0014_promotion_policy_gate.sql',
    'packages/supervisor/policy/promotion_gate.py',
    'scripts/verify_promotion_policy_gate.sh',
    'docs/operations/promotion-policy-gate-runbook.md',
  ]) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('promotion policy gate migration defines policy and admission tables', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0014_promotion_policy_gate.sql'), 'utf8');
  for (const needle of ['promotion_policy_versions', 'paper_trade_admissions']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('orchestration inserts promotion gate before paper portfolio', () => {
  const orchestration = readFileSync(path.join(repo, 'packages/supervisor/orchestration/run_supervisor_cycle.py'), 'utf8');
  assert.match(orchestration, /evaluate_promotion_gate/);
  const gateIdx = orchestration.indexOf('evaluate_promotion_gate');
  const portfolioIdx = orchestration.indexOf('run_paper_portfolio');
  assert.equal(gateIdx < portfolioIdx, true, 'promotion gate should run before paper portfolio');
});

test('paper portfolio now depends on explicit admissions', () => {
  const engine = readFileSync(path.join(repo, 'packages/supervisor/portfolio/paper_order_engine.py'), 'utf8');
  assert.match(engine, /FROM paper_trade_admissions/);
  assert.match(engine, /admission_status != 'admitted'/);
});

test('default promotion policy keeps paper trading disabled', () => {
  const rules = readFileSync(path.join(repo, 'packages/supervisor/policy/default_rules.py'), 'utf8');
  assert.match(rules, /paper_trading_enabled': False/);
});
