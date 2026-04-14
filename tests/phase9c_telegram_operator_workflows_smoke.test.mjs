import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();
const files = [
  'packages/db/migrations/0010_delivery_events.sql',
  'packages/supervisor/delivery/telegram.py',
  'packages/supervisor/delivery/events.py',
  'packages/supervisor/delivery/dispatch_pending_approvals.py',
  'scripts/verify_phase9c_telegram_operator_workflows.sh',
  'docs/operations/phase9c-telegram-operator-workflows-runbook.md',
  'docs/plans/2026-04-14-vietmarket-phase-9c-telegram-operator-workflows-execution.md',
];

test('Phase 9C required files exist', () => {
  for (const file of files) assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
});

test('Phase 9C migration defines delivery events ledger', () => {
  const sql = readFileSync(path.join(repo, 'packages/db/migrations/0010_delivery_events.sql'), 'utf8');
  assert.match(sql, /CREATE TABLE IF NOT EXISTS delivery_events/);
});

test('Phase 9C telegram delivery supports Bot API send and dry-run fallback', () => {
  const telegram = readFileSync(path.join(repo, 'packages/supervisor/delivery/telegram.py'), 'utf8');
  assert.match(telegram, /TELEGRAM_BOT_TOKEN/);
  assert.match(telegram, /sendMessage/);
  assert.match(telegram, /dry_run/);
});

test('Phase 9C verify script dispatches daily, alerts, and approvals', () => {
  const verify = readFileSync(path.join(repo, 'scripts/verify_phase9c_telegram_operator_workflows.sh'), 'utf8');
  for (const needle of ['dispatch_daily_brief.py', 'dispatch_intraday_alerts.py', 'dispatch_pending_approvals.py', 'delivery_events']) {
    assert.match(verify, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});
