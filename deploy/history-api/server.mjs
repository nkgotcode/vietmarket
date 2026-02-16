import express from 'express';

const app = express();

const PORT = Number(process.env.PORT || 8787);
const API_KEY = process.env.API_KEY || '';
const CLICKHOUSE_URL = (process.env.CLICKHOUSE_URL || 'http://127.0.0.1:8123').replace(/\/$/, '');
const CLICKHOUSE_DB = process.env.CLICKHOUSE_DB || 'vietmarket';

function authOk(req) {
  if (!API_KEY) return false;
  return req.get('x-api-key') === API_KEY;
}

app.get('/healthz', async (_req, res) => {
  res.json({ ok: true });
});

app.get('/candles', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.query.ticker || '').trim().toUpperCase();
  const tf = String(req.query.tf || '').trim();
  const beforeTs = req.query.beforeTs ? Number(req.query.beforeTs) : null;
  const limit = Math.min(Math.max(Number(req.query.limit || 500), 1), 2000);

  if (!ticker || !tf) return res.status(400).json({ ok: false, error: 'missing ticker/tf' });

  // ClickHouse ts is DateTime64; we use ms epoch for API.
  // Query returns newest-first; client can reverse if needed.
  const where = [
    `ticker = {ticker:String}`,
    `tf = {tf:String}`,
    beforeTs ? `ts < fromUnixTimestamp64Milli({before:UInt64})` : null,
  ].filter(Boolean).join(' AND ');

  const sql = `
SELECT
  toUnixTimestamp64Milli(ts) AS ts,
  o,h,l,c,
  v,
  source
FROM ${CLICKHOUSE_DB}.candles
WHERE ${where}
ORDER BY ts DESC
LIMIT {limit:UInt32}
FORMAT JSON
  `.trim();

  const params = {
    ticker,
    tf,
    limit,
    ...(beforeTs ? { before: Math.floor(beforeTs) } : {}),
  };

  const url = `${CLICKHOUSE_URL}/?query=${encodeURIComponent(sql)}&param_ticker=${encodeURIComponent(params.ticker)}&param_tf=${encodeURIComponent(params.tf)}&param_limit=${encodeURIComponent(String(params.limit))}` + (beforeTs ? `&param_before=${encodeURIComponent(String(params.before))}` : '');

  try {
    const r = await fetch(url);
    if (!r.ok) {
      const text = await r.text();
      return res.status(502).json({ ok: false, error: 'clickhouse_error', status: r.status, body: text.slice(0, 500) });
    }
    const j = await r.json();
    const rows = (j?.data || []).map((x) => ({
      ts: Number(x.ts),
      o: Number(x.o),
      h: Number(x.h),
      l: Number(x.l),
      c: Number(x.c),
      v: x.v == null ? null : Number(x.v),
      source: x.source ?? null,
    }));

    res.json({ ok: true, ticker, tf, count: rows.length, rows });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`history-api listening on :${PORT}`);
});
