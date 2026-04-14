import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

const requiredFiles = [
  'packages/db/migrations/0004_signal_engine.sql',
  'packages/supervisor/signals/common.py',
  'packages/supervisor/signals/trend.py',
  'packages/supervisor/signals/momentum.py',
  'packages/supervisor/signals/catalyst.py',
  'packages/supervisor/signals/fundamentals.py',
  'packages/supervisor/signals/liquidity.py',
  'packages/supervisor/signals/risk.py',
  'packages/supervisor/signals/build_signals.py',
  'packages/supervisor/signals/rank_candidates.py',
  'apps/web/src/app/api/brain/signals/route.ts',
  'apps/web/src/app/api/brain/candidates/route.ts',
  'apps/web/src/app/app/signals/page.tsx',
  'apps/web/src/components/signals/SignalsDashboard.tsx',
  'apps/web/src/components/signals/SignalBreakdownTable.tsx',
  'apps/web/src/components/signals/CandidateRankingTable.tsx',
  'scripts/verify_phase3_signal_engine.sh',
  'docs/operations/phase3-signal-engine-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-3-signal-engine-execution.md',
];

test('Phase 3 required files exist', () => {
  for (const file of requiredFiles) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 3 migration defines signal engine tables', () => {
  const sql = readFileSync(path.join(repo, 'packages/db/migrations/0004_signal_engine.sql'), 'utf8');
  for (const table of ['signal_scores', 'signal_components', 'signal_policies', 'candidate_rankings']) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
  }
});

test('signal build and ranking scripts use Phase 1 worker telemetry', () => {
  const buildSignals = readFileSync(path.join(repo, 'packages/supervisor/signals/build_signals.py'), 'utf8');
  const rankCandidates = readFileSync(path.join(repo, 'packages/supervisor/signals/rank_candidates.py'), 'utf8');
  assert.match(buildSignals, /write_worker_run/);
  assert.match(buildSignals, /write_failure/);
  assert.match(rankCandidates, /write_worker_run/);
  assert.match(rankCandidates, /write_failure/);
});

test('Phase 3 verification flow includes signal build and candidate ranking', () => {
  const verifyScript = readFileSync(path.join(repo, 'scripts/verify_phase3_signal_engine.sh'), 'utf8');
  const runbook = readFileSync(path.join(repo, 'docs/operations/phase3-signal-engine-runbook.md'), 'utf8');
  assert.match(verifyScript, /build_signals\.py/);
  assert.match(verifyScript, /rank_candidates\.py/);
  assert.match(runbook, /Build Phase 3 signal scores/);
  assert.match(runbook, /Build candidate rankings/);
});

test('Phase 3 APIs and UI expose signal and candidate outputs', () => {
  const signalsRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/signals/route.ts'), 'utf8');
  const candidatesRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/candidates/route.ts'), 'utf8');
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/signals/SignalsDashboard.tsx'), 'utf8');
  assert.match(signalsRoute, /signal_scores/);
  assert.match(signalsRoute, /signal_components/);
  assert.match(candidatesRoute, /candidate_rankings/);
  assert.match(dashboard, /Ranked candidates/);
  assert.match(dashboard, /Signal breakdowns/);
});
