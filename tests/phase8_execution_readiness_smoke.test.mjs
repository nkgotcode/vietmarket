import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
const repo = process.cwd();
const files = ['packages/db/migrations/0008_execution_readiness.sql','packages/supervisor/execution/broker_interface.py','packages/supervisor/execution/approval_gate.py','packages/supervisor/execution/stage_order.py','packages/supervisor/execution/reconcile_broker_state.py','apps/web/src/app/api/brain/execution-staging/route.ts','apps/web/src/app/api/brain/approvals/route.ts','apps/web/src/components/execution/ApprovalQueue.tsx','apps/web/src/app/app/execution/page.tsx','scripts/verify_phase8_execution_readiness.sh','docs/operations/phase8-execution-readiness-runbook.md'];

test('Phase 8 required files exist',()=>{for(const f of files) assert.equal(existsSync(path.join(repo,f)), true, `missing ${f}`);});
test('Phase 8 migration defines execution readiness tables',()=>{const sql=readFileSync(path.join(repo,'packages/db/migrations/0008_execution_readiness.sql'),'utf8'); for(const t of ['broker_accounts','broker_order_staging','broker_order_audit','broker_positions_mirror','execution_approvals']) assert.match(sql,new RegExp(`CREATE TABLE IF NOT EXISTS ${t}`));});
