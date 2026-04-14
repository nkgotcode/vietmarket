import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'apps/web/src/app/api/brain/delivery/route.ts',
  'apps/web/src/app/app/delivery/page.tsx',
  'apps/web/src/components/execution/DeliveryEventsTable.tsx',
  'tests/phase9d_hardening_smoke.test.mjs',
];

test('Phase 9D required hardening files exist', () => {
  for (const file of files) assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
});

test('Phase 9D delivery API reads delivery_events', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/delivery/route.ts'), 'utf8');
  assert.match(route, /delivery_events/);
});

test('Phase 9D approvals route supports POST transitions and audit writes', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/approvals/route.ts'), 'utf8');
  assert.match(route, /export async function POST/);
  assert.match(route, /broker_order_staging/);
  assert.match(route, /broker_order_audit/);
  assert.match(route, /execution_approvals/);
});

test('Phase 9D app home links to delivery page', () => {
  const page = readFileSync(path.join(repo, 'apps/web/src/app/app/page.tsx'), 'utf8');
  assert.match(page, /\/app\/delivery/);
});
