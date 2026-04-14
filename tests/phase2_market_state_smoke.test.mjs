import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

const requiredFiles = [
  'packages/db/migrations/0002_market_state.sql',
  'packages/db/migrations/0003_symbol_classification.sql',
  'packages/supervisor/snapshots/common.py',
  'packages/supervisor/snapshots/ticker_snapshot_builder.py',
  'packages/supervisor/snapshots/sector_snapshot_builder.py',
  'packages/supervisor/snapshots/regime_builder.py',
  'packages/supervisor/snapshots/build_market_state.py',
  'packages/ingest/vn/symbol_classification_sync.py',
  'deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl',
  'apps/web/src/app/api/brain/regime/route.ts',
  'apps/web/src/app/api/brain/watchlist/route.ts',
  'apps/web/src/app/api/brain/ticker/[ticker]/route.ts',
  'apps/web/src/app/api/brain/sectors/route.ts',
  'apps/web/src/app/app/regime/page.tsx',
  'apps/web/src/app/app/watchlist/page.tsx',
  'apps/web/src/app/app/ticker-state/[ticker]/page.tsx',
  'apps/web/src/components/market/RegimeCard.tsx',
  'apps/web/src/components/market/WatchlistTable.tsx',
  'apps/web/src/components/market/TickerSnapshotCard.tsx',
  'tests/phase2_market_state_smoke.test.mjs',
  'scripts/verify_phase2_market_state.sh',
  'docs/operations/phase2-market-state-runbook.md',
];

test('Phase 2 required files exist', () => {
  for (const file of requiredFiles) {
    assert.equal(existsSync(path.join(repo, file)), true, `missing ${file}`);
  }
});

test('Phase 2 migrations define market-state and symbol-classification schema', () => {
  const phase2Sql = readFileSync(path.join(repo, 'packages/db/migrations/0002_market_state.sql'), 'utf8');
  for (const table of ['market_state_cycles', 'ticker_snapshots', 'sector_snapshots', 'market_regime_snapshots']) {
    assert.match(phase2Sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}`));
  }
  const classSql = readFileSync(path.join(repo, 'packages/db/migrations/0003_symbol_classification.sql'), 'utf8');
  for (const token of ['icb_code', 'industry_code', 'sector_name', 'industry_name', 'classification_source']) {
    assert.match(classSql, new RegExp(token));
  }
});

test('market state verification flow includes canonical classification sync', () => {
  const verifyScript = readFileSync(path.join(repo, 'scripts/verify_phase2_market_state.sh'), 'utf8');
  const runbook = readFileSync(path.join(repo, 'docs/operations/phase2-market-state-runbook.md'), 'utf8');
  const nomadJob = readFileSync(path.join(repo, 'deploy/nomad/jobs/vietmarket-symbol-classification-sync.nomad.hcl'), 'utf8');
  assert.match(verifyScript, /symbol_classification_sync\.py/);
  assert.match(runbook, /Sync canonical symbol classification/);
  assert.match(runbook, /Nomad automation/);
  assert.match(nomadJob, /symbol_classification_sync\.py/);
  assert.match(nomadJob, /25 \*\/6 \* \* \*/);
});

test('ticker snapshots consume canonical symbol classification fields', () => {
  const builder = readFileSync(path.join(repo, 'packages/supervisor/snapshots/ticker_snapshot_builder.py'), 'utf8');
  assert.match(builder, /sector_name/);
  assert.match(builder, /industry_name/);
  assert.match(builder, /classification_source/);
});

test('candle ingestion active path remains direct Postgres upsert', () => {
  const batchRun = readFileSync(path.join(repo, 'packages/ingest/vn/candles_batch_run.sh'), 'utf8');
  const backfill = readFileSync(path.join(repo, 'packages/ingest/vn/candles_backfill.py'), 'utf8');
  assert.match(batchRun, /packages\/ingest\/vn\/candles_backfill\.py/);
  assert.match(backfill, /upsert_candles/);
  assert.doesNotMatch(backfill, /api\/mutation/);
});

test('watchlist and ticker UI expose classification codes explicitly', () => {
  const watchlistRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/watchlist/route.ts'), 'utf8');
  const tickerRoute = readFileSync(path.join(repo, 'apps/web/src/app/api/brain/ticker/[ticker]/route.ts'), 'utf8');
  const watchlistTable = readFileSync(path.join(repo, 'apps/web/src/components/market/WatchlistTable.tsx'), 'utf8');
  const tickerCard = readFileSync(path.join(repo, 'apps/web/src/components/market/TickerSnapshotCard.tsx'), 'utf8');
  const plan = readFileSync(path.join(repo, 'docs/plans/2026-04-14-vietmarket-phase-2-market-state-execution.md'), 'utf8');
  assert.match(watchlistRoute, /industry_name/);
  assert.match(watchlistRoute, /icb_code/);
  assert.match(watchlistRoute, /industry_code/);
  assert.match(tickerRoute, /industry_name/);
  assert.match(tickerRoute, /icb_code/);
  assert.match(tickerRoute, /industry_code/);
  assert.match(watchlistTable, /ICB \{row\.icb_code/);
  assert.match(tickerCard, /ICB \{snapshot\.icb_code/);
  assert.match(plan, /Timescale\/Postgres-only/i);
  assert.match(plan, /classification codes/i);
});
