import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

test('ingest script runs and emits result JSON', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'simplize-ingest-'));
  const run = spawnSync(process.execPath, [
    'scripts/simplize_ingest.mjs',
    '--tickers', 'FPT',
    '--period', 'Q',
    '--size', '2',
    '--out-dir', dir,
  ], {
    cwd: process.cwd(),
    encoding: 'utf8',
    timeout: 120000,
  });

  assert.equal(run.status, 0, run.stderr || run.stdout);
  const out = JSON.parse(run.stdout);
  assert.equal(out.ok, true);
  assert.equal(Array.isArray(out.results), true);
  assert.equal(out.results[0].ticker, 'FPT');

  const latest = path.join(dir, 'raw', 'FPT_Q_latest.json');
  assert.equal(existsSync(latest), true);

  const latestBody = JSON.parse(readFileSync(latest, 'utf8'));
  assert.equal(latestBody.ticker, 'FPT');
});
