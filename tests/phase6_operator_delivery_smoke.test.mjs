import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
const repo = process.cwd();
const files = [
 'packages/supervisor/delivery/formatter.py','packages/supervisor/delivery/telegram.py','packages/supervisor/delivery/dispatch_daily_brief.py','packages/supervisor/delivery/dispatch_intraday_alerts.py','packages/supervisor/reports/generate_decision_journal.py','apps/web/src/app/api/brain/journal/route.ts','apps/web/src/app/api/brain/alerts/route.ts','apps/web/src/app/app/journal/page.tsx','apps/web/src/app/app/alerts/page.tsx','apps/web/src/app/app/system/page.tsx','scripts/verify_phase6_operator_delivery.sh','docs/operations/phase6-operator-delivery-runbook.md'];

test('Phase 6 required files exist',()=>{for(const f of files) assert.equal(existsSync(path.join(repo,f)), true, `missing ${f}`);});
test('Phase 6 APIs expose journal and alerts',()=>{assert.match(readFileSync(path.join(repo,'apps/web/src/app/api/brain/journal/route.ts'),'utf8'), /supervisor_decisions/);assert.match(readFileSync(path.join(repo,'apps/web/src/app/api/brain/alerts/route.ts'),'utf8'), /policy_results/);});
