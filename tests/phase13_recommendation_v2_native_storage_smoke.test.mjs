import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('recommendation v2 native storage files exist', () => {
  for (const file of [
    'packages/db/migrations/0013_recommendation_v2_storage.sql',
    'scripts/verify_recommendation_v2_storage.sh',
    'docs/operations/recommendation-v2-native-storage-runbook.md',
  ]) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('recommendation v2 migration defines scorecard and promotion tables', () => {
  const migration = readFileSync(path.join(repo, 'packages/db/migrations/0013_recommendation_v2_storage.sql'), 'utf8');
  for (const needle of ['recommendation_scorecards', 'promotion_decisions']) {
    assert.match(migration, new RegExp(needle));
  }
});

test('recommendation generator writes native v2 storage tables', () => {
  const script = readFileSync(path.join(repo, 'packages/supervisor/recommendations/generate_recommendations.py'), 'utf8');
  for (const needle of ['INSERT INTO recommendation_scorecards', 'INSERT INTO promotion_decisions', 'new_promotion_decision_id']) {
    assert.match(script, new RegExp(needle));
  }
});

test('readers prefer native v2 storage tables', () => {
  const route = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/recommendations/route.ts'), 'utf8');
  const daily = readFileSync(path.join(repo, 'packages/supervisor/reports/generate_daily_brief.py'), 'utf8');
  for (const needle of ['recommendation_scorecards', 'promotion_decisions']) {
    assert.match(route, new RegExp(needle));
    assert.match(daily, new RegExp(needle));
  }
});
