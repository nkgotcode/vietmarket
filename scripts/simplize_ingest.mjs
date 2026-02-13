#!/usr/bin/env node

import { mkdir, readFile, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';
import { fetchTickerBlock, blockHash, normalizeBlock } from '../lib/simplize_pipeline.mjs';
import { resolveEffectivePeriod } from '../lib/simplize_config.mjs';

function parseArgs(argv) {
  const out = {
    tickers: ['FPT', 'VNM'],
    period: 'Q',
    size: 12,
    outDir: 'data/simplize',
    token: process.env.SIMPLIZE_BEARER || null,
    allowFallbackToQ: true,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--tickers') {
      out.tickers = String(v || '')
        .split(',')
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean);
      i++;
    } else if (a === '--period' || a === '-p') {
      out.period = String(v || '').toUpperCase();
      i++;
    } else if (a === '--size' || a === '-s') {
      out.size = Number(v || 12);
      i++;
    } else if (a === '--out-dir') {
      out.outDir = String(v || out.outDir);
      i++;
    } else if (a === '--token') {
      out.token = String(v || '').trim() || null;
      i++;
    } else if (a === '--no-fallback-to-q') {
      out.allowFallbackToQ = false;
    } else if (a === '--help' || a === '-h') {
      console.log('Usage: node scripts/simplize_ingest.mjs --tickers FPT,VNM --period Q --size 12 --out-dir data/simplize [--token <bearer>] [--no-fallback-to-q]');
      process.exit(0);
    }
  }

  if (!['Q', 'Y'].includes(out.period)) throw new Error('period must be Q or Y');
  if (!out.tickers.length) throw new Error('at least one ticker is required');
  if (!Number.isFinite(out.size) || out.size <= 0) throw new Error('size must be > 0');
  return out;
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch {
    return fallback;
  }
}

async function atomicWrite(file, content) {
  const tmp = `${file}.tmp`;
  await writeFile(tmp, content, 'utf8');
  await rename(tmp, file);
}

function keyOf({ ticker, period }) {
  return `${ticker}:${period}`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const now = new Date();
  const stamp = now.toISOString().replace(/[:]/g, '-');

  const outDir = path.resolve(args.outDir);
  const rawDir = path.join(outDir, 'raw');
  const dayDir = path.join(rawDir, now.toISOString().slice(0, 10));
  const normDir = path.join(outDir, 'normalized');
  const stateFile = path.join(outDir, 'state.json');

  await mkdir(rawDir, { recursive: true });
  await mkdir(dayDir, { recursive: true });
  await mkdir(normDir, { recursive: true });

  const state = await readJson(stateFile, { hashes: {} });
  const results = [];

  const periodDecision = resolveEffectivePeriod({
    requestedPeriod: args.period,
    hasAuthToken: Boolean(args.token),
    allowFallback: args.allowFallbackToQ,
  });

  for (const ticker of args.tickers) {
    const requestOptions = args.token
      ? { headers: { authorization: `Bearer ${args.token}` } }
      : {};

    const block = await fetchTickerBlock({
      ticker,
      period: periodDecision.effectivePeriod,
      size: args.size,
      requestOptions,
    });

    const hash = blockHash(block);
    const k = keyOf({ ticker, period: periodDecision.effectivePeriod });
    const prevHash = state.hashes[k] ?? null;
    const changed = prevHash !== hash;

    const latestFile = path.join(rawDir, `${ticker}_${periodDecision.effectivePeriod}_latest.json`);
    await atomicWrite(latestFile, JSON.stringify(block, null, 2));

    if (changed) {
      const snapFile = path.join(dayDir, `${ticker}_${periodDecision.effectivePeriod}_${stamp}.json`);
      await atomicWrite(snapFile, JSON.stringify(block, null, 2));

      const rows = normalizeBlock(block);
      const ndjsonPath = path.join(normDir, `${ticker}_${periodDecision.effectivePeriod}.ndjson`);
      const payload = rows.map((r) => JSON.stringify(r)).join('\n') + (rows.length ? '\n' : '');
      if (payload) {
        const prev = await readFile(ndjsonPath, 'utf8').catch(() => '');
        await atomicWrite(ndjsonPath, prev + payload);
      }
    }

    state.hashes[k] = hash;
    results.push({
      ticker,
      requestedPeriod: args.period,
      effectivePeriod: periodDecision.effectivePeriod,
      fallbackApplied: periodDecision.fallbackApplied,
      changed,
      hash,
    });
  }

  await atomicWrite(stateFile, JSON.stringify(state, null, 2));

  console.log(JSON.stringify({
    ok: true,
    at: now.toISOString(),
    outDir,
    periodDecision,
    results,
  }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
