#!/usr/bin/env node

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fetchUniverse, fetchUniverseFromSearch, chunk } from '../lib/simplize_universe.mjs';

function parseArgs(argv) {
  const out = {
    period: 'Q',
    size: 12,
    chunkSize: 100,
    maxChunks: 2,
    outDir: 'data/simplize',
    cursorFile: null,
    token: process.env.SIMPLIZE_BEARER || null,
    tokenFile: null,
    universeFile: null,
    dryRun: false,

    // Safety: never hang forever in schedulers.
    timeBudgetSec: Number(process.env.TIME_BUDGET_SEC || 0) || 15 * 60,
    heartbeatSec: Number(process.env.HEARTBEAT_SEC || 0) || 30,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--period' || a === '-p') { out.period = String(v || out.period).toUpperCase(); i++; }
    else if (a === '--size' || a === '-s') { out.size = Number(v || out.size); i++; }
    else if (a === '--chunk-size') { out.chunkSize = Number(v || out.chunkSize); i++; }
    else if (a === '--max-chunks') { out.maxChunks = Number(v || out.maxChunks); i++; }
    else if (a === '--out-dir') { out.outDir = String(v || out.outDir); i++; }
    else if (a === '--cursor-file') { out.cursorFile = String(v || '').trim() || null; i++; }
    else if (a === '--token') { out.token = String(v || '').trim() || null; i++; }
    else if (a === '--token-file') { out.tokenFile = String(v || '').trim() || null; i++; }
    else if (a === '--universe-file') { out.universeFile = String(v || '').trim() || null; i++; }
    else if (a === '--dry-run') { out.dryRun = true; }
    else if (a === '--time-budget-sec') { out.timeBudgetSec = Number(v || out.timeBudgetSec); i++; }
    else if (a === '--heartbeat-sec') { out.heartbeatSec = Number(v || out.heartbeatSec); i++; }
    else if (a === '--help' || a === '-h') {
      console.log('Usage: node scripts/simplize_expand_market.mjs --period Q --chunk-size 100 --max-chunks 3 --out-dir data/simplize [--token-file <path>] [--universe-file <path>] [--time-budget-sec 900] [--heartbeat-sec 30] [--dry-run]');
      process.exit(0);
    }
  }

  if (!['Q', 'Y'].includes(out.period)) throw new Error('period must be Q or Y');
  if (!Number.isFinite(out.chunkSize) || out.chunkSize <= 0) throw new Error('chunk-size must be > 0');
  if (!Number.isFinite(out.maxChunks) || out.maxChunks <= 0) throw new Error('max-chunks must be > 0');
  return out;
}

async function loadToken(args) {
  if (args.token) return args.token;
  if (!args.tokenFile) return null;
  return (await readFile(path.resolve(args.tokenFile), 'utf8').catch(() => '')).trim() || null;
}

async function readCursor(file) {
  try { return JSON.parse(await readFile(file, 'utf8')); } catch { return { nextChunk: 0 }; }
}

async function writeCursor(file, obj) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(obj, null, 2));
}

function runIngest({ tickers, period, size, outDir, token }) {
  const cmd = [
    'scripts/simplize_ingest.mjs',
    '--tickers', tickers.join(','),
    '--period', period,
    '--size', String(size),
    '--out-dir', outDir,
  ];
  if (token) cmd.push('--token', token);

  const r = spawnSync(process.execPath, cmd, {
    cwd: process.cwd(),
    encoding: 'utf8',
    timeout: 1000 * 60 * 25,
    maxBuffer: 1024 * 1024 * 10,
  });

  if (r.status !== 0) {
    throw new Error(`ingest failed: ${r.stderr || r.stdout || 'unknown error'}`);
  }
  return JSON.parse(r.stdout);
}

async function loadUniverse(args) {
  if (args.universeFile) {
    const text = await readFile(path.resolve(args.universeFile), 'utf8');
    const tickers = text
      .split(/[,\n\r\s]+/)
      .map((x) => x.trim().toUpperCase())
      .filter((x) => /^[A-Z0-9._-]{2,10}$/.test(x));
    const uniq = [...new Set(tickers)];
    return { ok: true, source: 'file', count: uniq.length, tickers: uniq };
  }

  const direct = await fetchUniverse();
  if (direct.ok && direct.count > 0) return direct;

  const search = await fetchUniverseFromSearch();
  return search;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  const startedWall = Date.now();
  const killTimer = setTimeout(() => {
    console.error(`TIMEOUT: simplize_expand_market exceeded time budget (${args.timeBudgetSec}s)`);
    process.exit(124);
  }, Math.max(10, args.timeBudgetSec) * 1000);
  killTimer.unref?.();

  const hb = setInterval(() => {
    const elapsed = Math.round((Date.now() - startedWall) / 1000);
    console.log(JSON.stringify({ ok: true, heartbeat: true, elapsedSec: elapsed, stage: globalThis.__STAGE__ || 'unknown' }));
  }, Math.max(5, args.heartbeatSec) * 1000);
  hb.unref?.();

  globalThis.__STAGE__ = 'loadToken';
  const token = await loadToken(args);

  globalThis.__STAGE__ = 'loadUniverse';
  console.log(JSON.stringify({ ok: true, stage: 'loadUniverse' }));
  const uni = await loadUniverse(args);
  if (!uni.ok || !uni.count) throw new Error('failed to build universe from all sources');

  // persist discovered universe for reproducibility
  await mkdir(path.resolve(args.outDir), { recursive: true });
  await writeFile(path.resolve(args.outDir, 'universe.latest.json'), JSON.stringify({
    at: new Date().toISOString(),
    source: uni.source,
    count: uni.count,
    tickers: uni.tickers,
  }, null, 2));

  const allChunks = chunk(uni.tickers, args.chunkSize);
  if (!allChunks.length) throw new Error('universe resolved but no chunks were built');
  const cursorPath = path.resolve(args.cursorFile || path.join(args.outDir, 'expand.cursor.json'));
  const cursor = await readCursor(cursorPath);
  const start = Math.max(0, Number(cursor.nextChunk || 0)) % Math.max(allChunks.length, 1);

  const selected = [];
  for (let i = 0; i < Math.min(args.maxChunks, allChunks.length); i++) {
    selected.push((start + i) % allChunks.length);
  }

  if (args.dryRun) {
    console.log(JSON.stringify({
      ok: true,
      dryRun: true,
      source: uni.source,
      totalTickers: uni.count,
      totalChunks: allChunks.length,
      chunkSize: args.chunkSize,
      selectedChunks: selected,
      sample: allChunks[selected[0]]?.slice(0, 10) || [],
    }, null, 2));
    return;
  }

  const startedAt = Date.now();
  const results = [];
  for (const chunkIdx of selected) {
    globalThis.__STAGE__ = `ingest chunk ${chunkIdx}`;
    const tickers = allChunks[chunkIdx];
    console.log(JSON.stringify({ ok: true, stage: 'ingest', chunk: chunkIdx, tickers: tickers.length, sample: tickers.slice(0, 5) }));
    const res = runIngest({ tickers, period: args.period, size: args.size, outDir: args.outDir, token });
    results.push({ chunk: chunkIdx, tickers: tickers.length, resultCount: res?.results?.length || 0 });
  }

  // rebuild publish json + sqlite after chunked run
  globalThis.__STAGE__ = 'publish';
  console.log(JSON.stringify({ ok: true, stage: 'publish' }));
  const pub = spawnSync(process.execPath, ['scripts/simplize_publish.mjs', '--in-dir', args.outDir, '--out-file', `${args.outDir}/publish/latest.json`], {
    cwd: process.cwd(), encoding: 'utf8', timeout: 120000,
  });
  if (pub.status !== 0) throw new Error(`publish failed: ${pub.stderr || pub.stdout}`);

  globalThis.__STAGE__ = 'sqlite_sync';
  console.log(JSON.stringify({ ok: true, stage: 'sqlite_sync' }));
  const db = spawnSync(process.execPath, ['scripts/simplize_sqlite_sync.mjs', '--raw-dir', `${args.outDir}/raw`, '--db-file', `${args.outDir}/simplize.db`], {
    cwd: process.cwd(), encoding: 'utf8', timeout: 120000,
  });
  if (db.status !== 0) throw new Error(`sqlite sync failed: ${db.stderr || db.stdout}`);

  const nextChunk = (selected[selected.length - 1] + 1) % allChunks.length;
  await writeCursor(cursorPath, {
    at: new Date().toISOString(),
    totalChunks: allChunks.length,
    nextChunk,
    lastSelected: selected,
  });

  console.log(JSON.stringify({
    ok: true,
    source: uni.source,
    totalUniverse: uni.count,
    chunkSize: args.chunkSize,
    totalChunks: allChunks.length,
    selectedChunks: selected,
    nextChunk,
    elapsedSec: Math.round((Date.now() - startedAt) / 1000),
    results,
  }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
