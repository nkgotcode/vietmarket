#!/usr/bin/env node

import { mkdir, readdir, readFile, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';

function parseArgs(argv) {
  const out = {
    inDir: 'data/simplize',
    outFile: 'data/simplize/publish/latest.json',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--in-dir') { out.inDir = String(v || out.inDir); i++; }
    else if (a === '--out-file') { out.outFile = String(v || out.outFile); i++; }
    else if (a === '--help' || a === '-h') {
      console.log('Usage: node scripts/simplize_publish.mjs --in-dir data/simplize --out-file data/simplize/publish/latest.json');
      process.exit(0);
    }
  }
  return out;
}

async function atomicWrite(file, content) {
  await mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp`;
  await writeFile(tmp, content, 'utf8');
  await rename(tmp, file);
}

async function readJson(file) {
  return JSON.parse(await readFile(file, 'utf8'));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const rawDir = path.resolve(args.inDir, 'raw');

  let files = [];
  try {
    files = await readdir(rawDir);
  } catch {
    files = [];
  }

  const latestFiles = files.filter((f) => /_latest\.json$/.test(f));
  const blocks = [];
  for (const f of latestFiles) {
    const file = path.join(rawDir, f);
    try {
      blocks.push(await readJson(file));
    } catch {
      // ignore bad file
    }
  }

  const byTickerPeriod = {};
  for (const b of blocks) {
    const key = `${b.ticker}:${b.period}`;
    byTickerPeriod[key] = b;
  }

  const output = {
    generatedAt: new Date().toISOString(),
    totalBlocks: blocks.length,
    index: Object.keys(byTickerPeriod).sort(),
    blocks: byTickerPeriod,
  };

  const outFile = path.resolve(args.outFile);
  await atomicWrite(outFile, JSON.stringify(output, null, 2));
  console.log(JSON.stringify({ ok: true, outFile, totalBlocks: blocks.length }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
