#!/usr/bin/env node

import path from 'node:path';
import { readFile } from 'node:fs/promises';
import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { openRegistryDb, upsertArticle, upsertArticleSymbol, upsertSymbol, upsertSymbolSource, rebuildContextLatest } from '../lib/registry_sqlite.mjs';
import { linkSymbolsFromText, linkSymbolsFromTitle } from '../lib/news_symbol_linker.mjs';

async function safeReadText(p, maxChars = 120000) {
  if (!p) return '';
  try {
    const buf = await readFile(p);
    return buf.toString('utf8', 0, Math.min(buf.length, maxChars));
  } catch {
    return '';
  }
}

function parseArgs(argv) {
  const out = {
    registryDb: 'data/registry/market_registry.db',
    vietstockDb: process.env.VIETSTOCK_ARCHIVE_DB || '/Users/lenamkhanh/vietstock-archive-data/archive.sqlite',
    knownTickersFile: 'data/simplize/universe.latest.json',
    batchSize: 500,
    cursorKey: 'vietstock.backfill.published_at',
    reset: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--registry-db') { out.registryDb = String(v); i++; }
    else if (a === '--vietstock-db') { out.vietstockDb = String(v); i++; }
    else if (a === '--known-tickers-file') { out.knownTickersFile = String(v); i++; }
    else if (a === '--batch-size') { out.batchSize = Number(v); i++; }
    else if (a === '--cursor-key') { out.cursorKey = String(v); i++; }
    else if (a === '--reset') { out.reset = true; }
  }
  return out;
}

function loadKnownTickers(filePath) {
  try {
    const uni = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const t = Array.isArray(uni?.tickers) ? uni.tickers : [];
    return new Set(t);
  } catch {
    return null;
  }
}

function kvGet(db, key) {
  const row = db.prepare('SELECT value FROM registry_kv WHERE key = ?').get(key);
  return row?.value ?? null;
}

function kvSet(db, key, value) {
  db.prepare(`
    INSERT INTO registry_kv (key, value, updatedAt)
    VALUES (?, ?, datetime('now'))
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updatedAt = excluded.updatedAt
  `).run(key, value);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const now = new Date().toISOString();

  const reg = openRegistryDb(path.resolve(args.registryDb));
  if (args.reset) kvSet(reg, args.cursorKey, '');

  const knownTickers = loadKnownTickers(path.resolve(args.knownTickersFile));

  const cursor = kvGet(reg, args.cursorKey) || '';

  const vdb = new DatabaseSync(path.resolve(args.vietstockDb));
  const rows = vdb.prepare(`
    SELECT url, title, published_at AS publishedAt, word_count AS wordCount, text_path AS textPath
    FROM articles
    WHERE fetch_status IN ('ok','fetched')
      AND published_at IS NOT NULL
      AND published_at > ?
    ORDER BY published_at ASC
    LIMIT ?
  `).all(cursor, Number(args.batchSize) || 500);

  let links = 0;
  for (const r of rows) {
    upsertArticle(reg, {
      url: r.url,
      title: r.title || r.url,
      publishedAt: r.publishedAt || null,
      wordCount: r.wordCount || null,
      source: 'vietstock',
      ingestedAt: now,
    });

    const body = await safeReadText(r.textPath);
    const hits = [
      ...linkSymbolsFromTitle(r.title, knownTickers),
      ...linkSymbolsFromText(body, knownTickers),
    ];
    for (const hit of hits) {
      upsertSymbol(reg, { ticker: hit.ticker, seenAt: now });
      upsertSymbolSource(reg, { ticker: hit.ticker, source: 'vietstock_extract', sourceRef: 'archive.sqlite', seenAt: now });
      upsertArticleSymbol(reg, { url: r.url, ticker: hit.ticker, confidence: hit.confidence, method: hit.method });
      links += 1;
    }
  }

  if (rows.length) {
    const last = rows[rows.length - 1].publishedAt;
    kvSet(reg, args.cursorKey, last);
  }

  // refresh materialized context (cheap)
  rebuildContextLatest(reg, now);

  const totalArticles = reg.prepare('SELECT COUNT(*) c FROM articles').get().c;
  const totalLinks = reg.prepare('SELECT COUNT(*) c FROM article_symbols').get().c;
  const newCursor = kvGet(reg, args.cursorKey);

  vdb.close();
  reg.close();

  console.log(JSON.stringify({
    ok: true,
    batch: rows.length,
    links,
    cursor: newCursor,
    totalArticles,
    totalLinks,
  }, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
