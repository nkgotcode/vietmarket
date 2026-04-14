import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
const repo = process.cwd();
const requiredFiles = [
  'packages/db/migrations/0006_portfolio_policy.sql',
  'packages/supervisor/policy/default_rules.py',
  'packages/supervisor/policy/checks.py',
  'packages/supervisor/policy/engine.py',
  'packages/supervisor/portfolio/paper_order_engine.py',
  'packages/supervisor/portfolio/fill_simulator.py',
  'packages/supervisor/portfolio/position_book.py',
  'packages/supervisor/portfolio/pnl.py',
  'packages/supervisor/reports/generate_portfolio_brief.py',
  'apps/web/src/app/api/brain/portfolio/route.ts',
  'apps/web/src/app/api/brain/orders/route.ts',
  'apps/web/src/app/api/brain/pnl/route.ts',
  'apps/web/src/app/api/brain/policy/route.ts',
  'apps/web/src/app/app/portfolio/page.tsx',
  'apps/web/src/app/app/orders/page.tsx',
  'apps/web/src/components/portfolio/PortfolioSummary.tsx',
  'apps/web/src/components/portfolio/PnLChart.tsx',
  'apps/web/src/components/portfolio/PolicyResultPanel.tsx',
  'scripts/verify_phase5_portfolio_policy.sh',
  'docs/operations/phase5-portfolio-policy-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-5-portfolio-policy-execution.md',
];

test('Phase 5 required files exist', () => { for (const file of requiredFiles) assert.equal(existsSync(path.join(repo,file)), true, `missing ${file}`); });

test('Phase 5 migration defines portfolio policy tables', () => {
 const sql = readFileSync(path.join(repo, 'packages/db/migrations/0006_portfolio_policy.sql'),'utf8');
 for (const table of ['policy_results','execution_intents','paper_orders','paper_fills','positions','portfolio_snapshots','position_events','risk_limits']) assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
});

test('Phase 5 policy and portfolio scripts persist durable outputs', () => {
 const engine = readFileSync(path.join(repo, 'packages/supervisor/policy/engine.py'),'utf8');
 const paper = readFileSync(path.join(repo, 'packages/supervisor/portfolio/paper_order_engine.py'),'utf8');
 assert.match(engine, /policy_results/);
 assert.match(paper, /paper_orders/);
 assert.match(paper, /portfolio_snapshots/);
});

test('Phase 5 APIs expose portfolio, orders, pnl, and policy', () => {
 const portfolio = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/portfolio/route.ts'),'utf8');
 const orders = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/orders/route.ts'),'utf8');
 const pnl = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/pnl/route.ts'),'utf8');
 const policy = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/policy/route.ts'),'utf8');
 assert.match(portfolio, /portfolio_snapshots/);
 assert.match(orders, /paper_orders/);
 assert.match(pnl, /portfolio_snapshots/);
 assert.match(policy, /policy_results/);
});
