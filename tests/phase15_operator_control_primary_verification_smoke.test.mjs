import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('operator control and writable-primary verification files exist', () => {
  for (const file of [
    'apps/web/src/app/api/brain/operator-control/route.ts',
    'apps/web/src/app/app/operator-control/page.tsx',
    'apps/web/src/components/operator/OperatorControlDashboard.tsx',
    'packages/supervisor/ops/inspect_db_target.py',
    'scripts/verify_writable_primary.sh',
    'docs/operations/operator-control-primary-verification-runbook.md',
  ]) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('operator control route exposes promotion policy, admissions, and writable-primary checks', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/operator-control/route.ts'), 'utf8');
  for (const needle of [
    'promotion_policy_versions',
    'paper_trade_admissions',
    'transaction_read_only',
    'pg_is_in_recovery()',
    'writable_primary',
  ]) {
    assert.match(route, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('db target inspector checks read-only and recovery status', () => {
  const inspector = readFileSync(path.join(repo, 'packages/supervisor/ops/inspect_db_target.py'), 'utf8');
  assert.match(inspector, /transaction_read_only/);
  assert.match(inspector, /pg_is_in_recovery\(\)/);
  assert.match(inspector, /writable_primary/);
});

test('home page links to operator control surface', () => {
  const home = readFileSync(path.join(repo, 'apps/web/src/app/app/page.tsx'), 'utf8');
  assert.match(home, /\/app\/operator-control/);
});
