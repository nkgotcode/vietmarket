import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

const requiredFiles = [
  'packages/db/migrations/0005_thesis_recommendation.sql',
  'packages/supervisor/theses/build_supervisor_packet.py',
  'packages/supervisor/theses/generate_theses.py',
  'packages/supervisor/recommendations/parse_structured_output.py',
  'packages/supervisor/recommendations/generate_recommendations.py',
  'packages/supervisor/reports/generate_daily_brief.py',
  'packages/supervisor/reports/generate_intraday_brief.py',
  'apps/web/src/app/api/brain/recommendations/route.ts',
  'apps/web/src/app/api/brain/theses/[ticker]/route.ts',
  'apps/web/src/app/api/brain/daily-brief/route.ts',
  'apps/web/src/app/app/recommendations/page.tsx',
  'apps/web/src/app/app/briefing/page.tsx',
  'apps/web/src/components/recommendations/RecommendationCard.tsx',
  'apps/web/src/components/recommendations/ThesisPanel.tsx',
  'apps/web/src/components/recommendations/RecommendationsDashboard.tsx',
  'scripts/verify_phase4_thesis_recommendation.sh',
  'docs/operations/phase4-thesis-recommendation-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-4-thesis-recommendation-execution.md',
];

test('Phase 4 required files exist', () => {
  for (const file of requiredFiles) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 4 migration defines thesis/recommendation tables', () => {
  const sql = readFileSync(path.join(repo, 'packages/db/migrations/0005_thesis_recommendation.sql'), 'utf8');
  for (const table of ['theses', 'recommendations', 'supervisor_decisions', 'daily_briefs', 'recommendation_outcomes']) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
  }
});

test('Phase 4 generator scripts use durable storage and worker telemetry', () => {
  const theses = readFileSync(path.join(repo, 'packages/supervisor/theses/generate_theses.py'), 'utf8');
  const recs = readFileSync(path.join(repo, 'packages/supervisor/recommendations/generate_recommendations.py'), 'utf8');
  const brief = readFileSync(path.join(repo, 'packages/supervisor/reports/generate_daily_brief.py'), 'utf8');
  assert.match(theses, /supervisor_decisions/);
  assert.match(theses, /write_worker_run/);
  assert.match(recs, /recommendations/);
  assert.match(recs, /write_worker_run/);
  assert.match(brief, /daily_briefs/);
  assert.match(brief, /write_worker_run/);
});

test('Phase 4 verification flow includes packet, theses, recommendations, and briefing', () => {
  const verifyScript = readFileSync(path.join(repo, 'scripts/verify_phase4_thesis_recommendation.sh'), 'utf8');
  const runbook = readFileSync(path.join(repo, 'docs/operations/phase4-thesis-recommendation-runbook.md'), 'utf8');
  assert.match(verifyScript, /build_supervisor_packet/);
  assert.match(verifyScript, /generate_theses\.py/);
  assert.match(verifyScript, /generate_recommendations\.py/);
  assert.match(verifyScript, /generate_daily_brief\.py/);
  assert.match(runbook, /Build bounded supervisor packet/);
  assert.match(runbook, /Generate recommendations/);
});

test('Phase 4 APIs and UI expose durable recommendation objects', () => {
  const recRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/recommendations/route.ts'), 'utf8');
  const thesisRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/theses/[ticker]/route.ts'), 'utf8');
  const briefRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/daily-brief/route.ts'), 'utf8');
  const dashboard = readFileSync(path.join(repo, 'apps/web/src/components/recommendations/RecommendationsDashboard.tsx'), 'utf8');
  assert.match(recRoute, /FROM recommendations/);
  assert.match(thesisRoute, /FROM theses/);
  assert.match(briefRoute, /FROM daily_briefs/);
  assert.match(dashboard, /recommendation objects/i);
});
