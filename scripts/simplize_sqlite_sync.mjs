#!/usr/bin/env node

import { mkdir, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { normalizeBlock } from '../lib/simplize_pipeline.mjs';
import { openDb, upsertRows } from '../lib/simplize_sqlite.mjs';

function parseArgs(argv) {
  const out = {
    rawDir: 'data/simplize/raw',
    dbFile: 'data/simplize/simplize.db',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--raw-dir') { out.rawDir = String(v || out.rawDir); i++; }
    else if (a === '--db-file') { out.dbFile = String(v || out.dbFile); i++; }
  }
  return out;
}

async function readJson(file) {
  return JSON.parse(await readFile(file, 'utf8'));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const rawDir = path.resolve(args.rawDir);
  const dbFile = path.resolve(args.dbFile);
  await mkdir(path.dirname(dbFile), { recursive: true });

  let files = [];
  try { files = await readdir(rawDir); } catch { files = []; }
  const latest = files.filter((f) => f.endsWith('_latest.json'));

  const allRows = [];
  for (const f of latest) {
    try {
      const block = await readJson(path.join(rawDir, f));
      allRows.push(...normalizeBlock(block));
    } catch {
      // ignore bad files
    }
  }

  const db = openDb(dbFile);
  upsertRows(db, allRows);
  db.close();

  console.log(JSON.stringify({ ok: true, dbFile, rowsUpserted: allRows.length, files: latest.length }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
