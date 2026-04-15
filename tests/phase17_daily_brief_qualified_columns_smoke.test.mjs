import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('daily brief recommendation query qualifies recommendation columns to avoid ambiguous joins', () => {
  const daily = readFileSync(path.join(repo, 'packages/supervisor/reports/generate_daily_brief.py'), 'utf8');
  assert.match(daily, /SELECT r\.ticker, r\.status, r\.side, r\.confidence, r\.suggested_priority, r\.summary,/);
  assert.match(daily, /WHERE r\.cycle_id = %s/);
  assert.match(daily, /ORDER BY r\.suggested_priority ASC, r\.confidence DESC, r\.ticker ASC/);
});
