#!/usr/bin/env node

import { stat } from 'node:fs/promises';
import path from 'node:path';
import { evaluateFreshness } from '../lib/simplize_health.mjs';

function parseArgs(argv) {
  const out = {
    outDir: 'data/simplize/raw',
    tickers: ['FPT', 'VNM', 'HPG'],
    period: 'Q',
    maxAgeMinutes: 120,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--out-dir') { out.outDir = String(v || out.outDir); i++; }
    else if (a === '--tickers') { out.tickers = String(v || '').split(',').map(x=>x.trim().toUpperCase()).filter(Boolean); i++; }
    else if (a === '--period' || a === '-p') { out.period = String(v || out.period).toUpperCase(); i++; }
    else if (a === '--max-age-minutes') { out.maxAgeMinutes = Number(v || out.maxAgeMinutes); i++; }
    else if (a === '--help' || a === '-h') {
      console.log('Usage: node scripts/simplize_healthcheck.mjs --tickers FPT,VNM --period Q --max-age-minutes 120');
      process.exit(0);
    }
  }
  return out;
}

async function mtimeMs(file) {
  try {
    const s = await stat(file);
    return s.mtimeMs;
  } catch {
    return null;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const now = Date.now();
  const maxAgeMs = args.maxAgeMinutes * 60 * 1000;

  const checks = await Promise.all(args.tickers.map(async (ticker) => {
    const file = path.join(args.outDir, `${ticker}_${args.period}_latest.json`);
    const lastMs = await mtimeMs(file);
    const r = evaluateFreshness(now, lastMs, maxAgeMs);
    return { ticker, file, ...r };
  }));

  const failed = checks.filter(c => !c.ok);
  if (failed.length) {
    console.log(JSON.stringify({ ok: false, maxAgeMinutes: args.maxAgeMinutes, failed, checks }, null, 2));
    process.exit(2);
  }

  console.log(JSON.stringify({ ok: true, maxAgeMinutes: args.maxAgeMinutes, checks }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
