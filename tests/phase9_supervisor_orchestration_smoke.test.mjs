import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0009_supervisor_orchestration.sql',
  'packages/supervisor/orchestration/__init__.py',
  'packages/supervisor/orchestration/run_supervisor_cycle.py',
  'deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl',
  'scripts/verify_phase9_supervisor_orchestration.sh',
  'docs/operations/phase9-supervisor-orchestration-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-9-productionization-sequence.md',
];

test('Phase 9 required files exist', () => {
  for (const file of files) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 9 migration defines supervisor orchestration tables', () => {
  const sql = readFileSync(path.join(repo, 'packages/db/migrations/0009_supervisor_orchestration.sql'), 'utf8');
  for (const table of ['supervisor_runs', 'supervisor_run_steps']) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
  }
});

test('Phase 9 orchestration runner wires the daily supervisor pipeline', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/orchestration/run_supervisor_cycle.py'), 'utf8');
  for (const needle of [
    'build_freshness.py',
    'build_system_health.py',
    'build_market_state.py',
    'build_signals.py',
    'rank_candidates.py',
    'generate_theses.py',
    'generate_recommendations.py',
    'paper_order_engine.py',
    'generate_daily_brief.py',
    'dispatch_daily_brief.py',
    'supervisor_runs',
    'supervisor_run_steps',
    '--strict-health-gate',
  ]) {
    assert.match(script, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('Phase 9 ids file exposes orchestration ids', () => {
  const ids = readFileSync(path.join(repo, 'packages/supervisor/common/ids.py'), 'utf8');
  assert.match(ids, /def new_supervisor_run_id\(/);
  assert.match(ids, /def new_supervisor_step_id\(/);
});

test('Phase 9 Nomad job schedules the daily cycle on OptiPlex', () => {
  const nomad = readFileSync(path.join(repo, 'deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl'), 'utf8');
  assert.match(nomad, /time_zone\s*=\s*"Asia\/Ho_Chi_Minh"/);
  assert.match(nomad, /value\s*=\s*"optiplex"/);
  assert.match(nomad, /run_supervisor_cycle\.py/);
  assert.match(nomad, /--mode", "daily"/);
  assert.match(nomad, /--strict-health-gate/);
});

test('Phase 9 verification script inspects orchestration ledger', () => {
  const verify = readFileSync(path.join(repo, 'scripts/verify_phase9_supervisor_orchestration.sh'), 'utf8');
  assert.match(verify, /supervisor_runs/);
  assert.match(verify, /supervisor_run_steps/);
  assert.match(verify, /run_supervisor_cycle.py/);
});
