#!/usr/bin/env node

import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

function parseArgs(argv) {
  const out = {
    port: 18991,
    source: 'data/simplize/publish/latest.json',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--port') { out.port = Number(v || out.port); i++; }
    else if (a === '--source') { out.source = String(v || out.source); i++; }
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

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://127.0.0.1:${args.port}`);
      if (url.pathname === '/health') {
        return sendJson(res, 200, { ok: true });
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
      return sendJson(res, 404, { ok: false, error: 'not_found' });
    } catch (err) {
      return sendJson(res, 500, { ok: false, error: err.message || String(err) });
    }
  });

  server.listen(args.port, '127.0.0.1', () => {
    console.log(JSON.stringify({ ok: true, port: args.port, source: sourceFile }));
  });
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
