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
  replaceFiLatest,
  rebuildContextLatest,
} from '../lib/registry_sqlite.mjs';
import { linkSymbolsFromText, linkSymbolsFromTitle } from '../lib/news_symbol_linker.mjs';

function parseArgs(argv) {
  const out = {
    simplizeDb: 'data/simplize/simplize.db',
    simplizeUniverse: 'data/simplize/universe.latest.json',
    vietstockExportsDir: 'exports/vietstock',
    vietstockDb: process.env.VIETSTOCK_ARCHIVE_DB || '/Users/lenamkhanh/vietstock-archive-data/archive.sqlite',
    vietstockDays: 30,
    registryDb: 'data/registry/market_registry.db',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]; const v = argv[i + 1];
    if (a === '--simplize-db') { out.simplizeDb = String(v); i++; }
    else if (a === '--simplize-universe') { out.simplizeUniverse = String(v); i++; }
    else if (a === '--vietstock-exports-dir') { out.vietstockExportsDir = String(v); i++; }
    else if (a === '--vietstock-db') { out.vietstockDb = String(v); i++; }
    else if (a === '--vietstock-days') { out.vietstockDays = Number(v); i++; }
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

async function safeReadText(p, maxChars = 80000) {
  if (!p) return '';
  try {
    const buf = await readFile(p);
    return buf.toString('utf8', 0, Math.min(buf.length, maxChars));
  } catch {
    return '';
  }
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

  // ingest Simplize DB distinct tickers + latest FI points
  const knownTickers = new Set(uniTickers);
  let fiLatestRows = [];
  try {
    const sdb = new DatabaseSync(path.resolve(args.simplizeDb));
    const rows = sdb.prepare('SELECT DISTINCT ticker, period FROM fi_points').all();
    for (const r of rows) {
      knownTickers.add(r.ticker);
      upsertSymbol(reg, { ticker: r.ticker, seenAt: now });
      upsertSymbolSource(reg, { ticker: r.ticker, source: 'simplize_fi_points', sourceRef: r.period, seenAt: now });
    }

    fiLatestRows = sdb.prepare(`
      SELECT f.ticker, f.period, f.statement, f.periodDate, f.metric, f.value, f.fetchedAt
      FROM fi_points f
      JOIN (
        SELECT ticker, period, statement, MAX(periodDate) AS maxPeriodDate
        FROM fi_points
        GROUP BY ticker, period, statement
      ) x
      ON f.ticker = x.ticker
      AND f.period = x.period
      AND f.statement = x.statement
      AND f.periodDate = x.maxPeriodDate
    `).all();
    sdb.close();
  } catch {}

  replaceFiLatest(reg, fiLatestRows);

  // ingest Vietstock exports (index.json) + inferred symbols (title + body)
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

      const body = await safeReadText(a.text_path);
      const linksFound = [
        ...linkSymbolsFromTitle(a.title, knownTickers),
        ...linkSymbolsFromText(body, knownTickers),
      ];
      for (const hit of linksFound) {
        upsertSymbol(reg, { ticker: hit.ticker, seenAt: now });
        upsertSymbolSource(reg, { ticker: hit.ticker, source: 'vietstock_extract', sourceRef: file, seenAt: now });
        upsertArticleSymbol(reg, { url: a.url, ticker: hit.ticker, confidence: hit.confidence, method: hit.method });
        links += 1;
      }
    }
  }

  // ingest Vietstock archive sqlite for broader coverage
  let archiveArticles = 0;
  let archiveLinks = 0;
  try {
    const vdb = new DatabaseSync(path.resolve(args.vietstockDb));
    const rows = vdb.prepare(`
      SELECT url, title, published_at AS publishedAt, word_count AS wordCount, text_path AS textPath
      FROM articles
      WHERE fetch_status IN ('ok','fetched')
        AND title IS NOT NULL
        AND url IS NOT NULL
        AND published_at >= datetime('now', ?)
    `).all(`-${Number(args.vietstockDays) || 30} day`);

    for (const r of rows) {
      upsertArticle(reg, {
        url: r.url,
        title: r.title,
        publishedAt: r.publishedAt || null,
        wordCount: r.wordCount || null,
        source: 'vietstock',
        ingestedAt: now,
      });
      archiveArticles += 1;
      const body = await safeReadText(r.textPath);
      const hits = [
        ...linkSymbolsFromTitle(r.title, knownTickers),
        ...linkSymbolsFromText(body, knownTickers),
      ];
      for (const hit of hits) {
        upsertSymbol(reg, { ticker: hit.ticker, seenAt: now });
        upsertSymbolSource(reg, { ticker: hit.ticker, source: 'vietstock_extract', sourceRef: 'archive.sqlite', seenAt: now });
        upsertArticleSymbol(reg, { url: r.url, ticker: hit.ticker, confidence: hit.confidence, method: hit.method });
        archiveLinks += 1;
      }
    }
    vdb.close();
  } catch {}

  rebuildContextLatest(reg, now);

  const symbolCount = reg.prepare('SELECT COUNT(*) c FROM symbols').get().c;
  const contextCount = reg.prepare('SELECT COUNT(*) c FROM symbol_context_latest').get().c;
  reg.close();

  console.log(JSON.stringify({
    ok: true,
    registryDb: registryPath,
    symbols: symbolCount,
    contextRows: contextCount,
    fiLatestRows: fiLatestRows.length,
    universeTickers: uniTickers.length,
    indexesScanned: indexes.length,
    articlesIngested: articleCount,
    archiveArticlesIngested: archiveArticles,
    articleSymbolLinks: links,
    archiveArticleSymbolLinks: archiveLinks,
  }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
