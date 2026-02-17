#!/usr/bin/env node

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fetchUniverse, fetchUniverseFromSearch } from '../lib/simplize_universe.mjs';

function parseArgs(argv) {
  const out = {
    outFile: 'data/simplize/universe.latest.json',
    timeoutMs: 20000,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = argv[i + 1];
    if (a === '--out-file') { out.outFile = String(v || out.outFile); i++; }
    else if (a === '--timeout-ms') { out.timeoutMs = Number(v || out.timeoutMs); i++; }
    else if (a === '--help' || a === '-h') {
      console.log('Usage: node scripts/simplize_universe_refresh.mjs [--out-file data/simplize/universe.latest.json]');
      process.exit(0);
    }
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  let uni = await fetchUniverse({ timeoutMs: args.timeoutMs }).catch(() => ({ ok: false, count: 0 }));
  if (!uni?.ok || !uni?.count) {
    const fb = await fetchUniverseFromSearch({ timeoutMs: Math.max(8000, Math.floor(args.timeoutMs * 0.6)) });
    uni = fb;
  }

  if (!uni?.count) throw new Error('failed to fetch Simplize universe from all sources');

  const outPath = path.resolve(args.outFile);
  await mkdir(path.dirname(outPath), { recursive: true });
  const payload = {
    at: new Date().toISOString(),
    source: uni.source,
    count: uni.count,
    tickers: uni.tickers,
  };
  await writeFile(outPath, JSON.stringify(payload, null, 2));

  console.log(JSON.stringify({ ok: true, outFile: outPath, source: uni.source, count: uni.count }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
