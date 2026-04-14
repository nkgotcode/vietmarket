import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
const repo = process.cwd();
const files = ['packages/db/migrations/0007_evaluation_governance.sql','packages/supervisor/common/prompt_registry.py','packages/supervisor/reports/evaluate_recommendations.py','packages/supervisor/reports/run_replay.py','packages/supervisor/reports/calibration.py','docs/operations/supervisor-runbook.md','docs/operations/degraded-mode.md','docs/operations/replay-runbook.md','docs/apis/supervisor-api.md','docs/architecture/data-model.md','scripts/verify_phase7_evaluation_governance.sh'];

test('Phase 7 required files exist',()=>{for(const f of files) assert.equal(existsSync(path.join(repo,f)), true, `missing ${f}`);});
test('Phase 7 migration defines evaluation governance tables',()=>{const sql=readFileSync(path.join(repo,'packages/db/migrations/0007_evaluation_governance.sql'),'utf8'); for(const t of ['replay_runs','replay_results','prompt_versions','model_runs','recommendation_outcomes','calibration_metrics']) assert.match(sql,new RegExp(`CREATE TABLE IF NOT EXISTS ${t}`));});
