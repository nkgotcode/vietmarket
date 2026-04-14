import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

const requiredFiles = [
  'packages/db/migrations/0001_control_plane.sql',
  'packages/db/sql/apply_migrations.py',
  'packages/supervisor/common/db.py',
  'packages/supervisor/health/freshness_builder.py',
  'packages/supervisor/health/system_health_builder.py',
  'apps/web/src/app/api/brain/health/route.ts',
  'apps/web/src/app/api/brain/freshness/route.ts',
  'apps/web/src/app/api/brain/workers/route.ts',
  'apps/web/src/app/app/health/page.tsx',
  'scripts/verify_phase1_control_plane.sh',
  'docs/operations/phase1-control-plane-runbook.md',
];

test('Phase 1 required files exist', () => {
  for (const file of requiredFiles) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 1 migration defines control-plane tables', () => {
  const sql = readFileSync(path.join(repo, 'packages/db/migrations/0001_control_plane.sql'), 'utf8');
  for (const table of ['worker_runs', 'worker_failures', 'dataset_freshness', 'system_health_snapshots', 'system_health_issues']) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
  }
});