#!/usr/bin/env node

import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { openDb, queryFi } from '../lib/simplize_sqlite.mjs';
import { openRegistryDb, querySymbols, queryContext } from '../lib/registry_sqlite.mjs';

function parseArgs(argv) {
  const out = {
    port: 18991,
    source: 'data/simplize/publish/latest.json',
    dbFile: 'data/simplize/simplize.db',
    registryDbFile: 'data/registry/market_registry.db',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--port') { out.port = Number(v || out.port); i++; }
    else if (a === '--source') { out.source = String(v || out.source); i++; }
    else if (a === '--db-file') { out.dbFile = String(v || out.dbFile); i++; }
    else if (a === '--registry-db-file') { out.registryDbFile = String(v || out.registryDbFile); i++; }
  }
  return out;
}

async function readSource(file) {
  const raw = await readFile(file, 'utf8');
  return JSON.parse(raw);
}

function sendJson(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const sourceFile = path.resolve(args.source);
  const dbPath = path.resolve(args.dbFile);
  const registryDbPath = path.resolve(args.registryDbFile);
  let db = null;
  let registryDb = null;
  try { db = openDb(dbPath); } catch { db = null; }
  try { registryDb = openRegistryDb(registryDbPath); } catch { registryDb = null; }

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://127.0.0.1:${args.port}`);
      if (url.pathname === '/health') {
        return sendJson(res, 200, { ok: true, db: Boolean(db), registryDb: Boolean(registryDb) });
      }
      if (url.pathname === '/fi') {
        const ticker = (url.searchParams.get('ticker') || '').toUpperCase();
        const period = (url.searchParams.get('period') || 'Q').toUpperCase();
        if (!ticker) return sendJson(res, 400, { ok: false, error: 'ticker is required' });

        const src = await readSource(sourceFile);
        const key = `${ticker}:${period}`;
        const block = src.blocks?.[key] || null;
        if (!block) return sendJson(res, 404, { ok: false, error: 'not_found', key });
        return sendJson(res, 200, { ok: true, key, block });
      }
      if (url.pathname === '/fi_rows') {
        if (!db) return sendJson(res, 503, { ok: false, error: 'db_unavailable' });
        const ticker = (url.searchParams.get('ticker') || '').toUpperCase();
        const period = (url.searchParams.get('period') || 'Q').toUpperCase();
        const statement = (url.searchParams.get('statement') || '').toLowerCase() || null;
        const limit = Number(url.searchParams.get('limit') || 500);
        if (!ticker) return sendJson(res, 400, { ok: false, error: 'ticker is required' });
        const rows = queryFi(db, { ticker, period, statement, limit });
        return sendJson(res, 200, { ok: true, ticker, period, statement, count: rows.length, rows });
      }
      if (url.pathname === '/symbols') {
        if (!registryDb) return sendJson(res, 503, { ok: false, error: 'registry_db_unavailable' });
        const q = url.searchParams.get('q') || '';
        const limit = Number(url.searchParams.get('limit') || 200);
        const rows = querySymbols(registryDb, { q, limit });
        return sendJson(res, 200, { ok: true, q, count: rows.length, rows });
      }
      if (url.pathname === '/context') {
        if (!registryDb) return sendJson(res, 503, { ok: false, error: 'registry_db_unavailable' });
        const ticker = (url.searchParams.get('ticker') || '').toUpperCase();
        const period = (url.searchParams.get('period') || 'Q').toUpperCase();
        if (!ticker) return sendJson(res, 400, { ok: false, error: 'ticker is required' });

        const ctx = queryContext(registryDb, { ticker, limitArticles: Number(url.searchParams.get('limitArticles') || 10) });
        let fi = [];
        if (db) {
          fi = queryFi(db, { ticker, period, limit: Number(url.searchParams.get('limitFi') || 200) });
        }
        return sendJson(res, 200, { ok: true, ticker, period, context: ctx, fiCount: fi.length, fi });
      }
      return sendJson(res, 404, { ok: false, error: 'not_found' });
    } catch (err) {
      return sendJson(res, 500, { ok: false, error: err.message || String(err) });
    }
  });

  server.listen(args.port, '127.0.0.1', () => {
    console.log(JSON.stringify({
      ok: true,
      port: args.port,
      source: sourceFile,
      dbPath,
      dbReady: Boolean(db),
      registryDbPath,
      registryReady: Boolean(registryDb),
    }));
  });

  process.on('SIGTERM', () => {
    try { db?.close(); } catch {}
    try { registryDb?.close(); } catch {}
    server.close(() => process.exit(0));
  });
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
