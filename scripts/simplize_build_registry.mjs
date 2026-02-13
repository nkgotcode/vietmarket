#!/usr/bin/env node

import { mkdir, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import {
  openRegistryDb,
  upsertSymbol,
  upsertSymbolSource,
  upsertArticle,
  upsertArticleSymbol,
} from '../lib/registry_sqlite.mjs';

const STOPWORDS = new Set(['ETF','USD','VND','VNINDEX','HNX','HOSE','UPCOM','CTCP','VNI']);

function extractTickers(text) {
  const out = new Set();
  for (const m of String(text || '').matchAll(/\b[A-Z]{2,5}\b/g)) {
    const tk = m[0].toUpperCase();
    if (STOPWORDS.has(tk)) continue;
    out.add(tk);
  }
  return [...out];
}

function parseArgs(argv) {
  const out = {
    simplizeDb: 'data/simplize/simplize.db',
    simplizeUniverse: 'data/simplize/universe.latest.json',
    vietstockExportsDir: 'exports/vietstock',
    registryDb: 'data/registry/market_registry.db',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = argv[i + 1];
    if (a === '--simplize-db') { out.simplizeDb = String(v); i++; }
    else if (a === '--simplize-universe') { out.simplizeUniverse = String(v); i++; }
    else if (a === '--vietstock-exports-dir') { out.vietstockExportsDir = String(v); i++; }
    else if (a === '--registry-db') { out.registryDb = String(v); i++; }
  }
  return out;
}

async function listIndexJson(root) {
  const files = [];
  async function walk(dir) {
    let ents = [];
    try { ents = await readdir(dir, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) await walk(p);
      else if (e.isFile() && e.name === 'index.json') files.push(p);
    }
  }
  await walk(root);
  return files;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const now = new Date().toISOString();

  const registryPath = path.resolve(args.registryDb);
  await mkdir(path.dirname(registryPath), { recursive: true });
  const reg = openRegistryDb(registryPath);

  // ingest Simplize universe file
  let uni = { tickers: [] };
  try { uni = JSON.parse(await readFile(path.resolve(args.simplizeUniverse), 'utf8')); } catch {}
  const uniTickers = Array.isArray(uni?.tickers) ? uni.tickers : [];
  for (const t of uniTickers) {
    upsertSymbol(reg, { ticker: t, seenAt: now });
    upsertSymbolSource(reg, { ticker: t, source: 'simplize_universe', sourceRef: 'universe.latest.json', seenAt: now });
  }

  // ingest Simplize DB distinct tickers
  try {
    const sdb = new DatabaseSync(path.resolve(args.simplizeDb));
    const rows = sdb.prepare('SELECT DISTINCT ticker, period FROM fi_points').all();
    for (const r of rows) {
      upsertSymbol(reg, { ticker: r.ticker, seenAt: now });
      upsertSymbolSource(reg, { ticker: r.ticker, source: 'simplize_fi_points', sourceRef: r.period, seenAt: now });
    }
    sdb.close();
  } catch {}

  // ingest Vietstock article indexes + inferred symbols
  const indexes = await listIndexJson(path.resolve(args.vietstockExportsDir));
  let articleCount = 0;
  let links = 0;
  for (const file of indexes) {
    let arr = [];
    try { arr = JSON.parse(await readFile(file, 'utf8')); } catch { continue; }
    if (!Array.isArray(arr)) continue;
    for (const a of arr) {
      if (!a?.url || !a?.title) continue;
      upsertArticle(reg, {
        url: a.url,
        title: a.title,
        publishedAt: a.published_at || null,
        wordCount: a.word_count || null,
        source: 'vietstock',
        ingestedAt: now,
      });
      articleCount += 1;

      const tks = extractTickers(a.title);
      for (const tk of tks) {
        upsertSymbol(reg, { ticker: tk, seenAt: now });
        upsertSymbolSource(reg, { ticker: tk, source: 'vietstock_title_extract', sourceRef: file, seenAt: now });
        upsertArticleSymbol(reg, { url: a.url, ticker: tk, confidence: 0.55, method: 'title_regex' });
        links += 1;
      }
    }
  }

  const symbolCount = reg.prepare('SELECT COUNT(*) c FROM symbols').get().c;
  reg.close();

  console.log(JSON.stringify({
    ok: true,
    registryDb: registryPath,
    symbols: symbolCount,
    universeTickers: uniTickers.length,
    indexesScanned: indexes.length,
    articlesIngested: articleCount,
    articleSymbolLinks: links,
  }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
