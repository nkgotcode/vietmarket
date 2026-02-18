import express from 'express';
import pg from 'pg';

const { Pool } = pg;

const app = express();

const PORT = Number(process.env.PORT || 8787);
const API_KEY = process.env.API_KEY || '';

// Example:
//   postgres://vietmarket:password@100.103.201.10:5432/vietmarket?sslmode=disable
const PG_URL = process.env.PG_URL || '';

function authOk(req) {
  if (!API_KEY) return false;
  return req.get('x-api-key') === API_KEY;
}

if (!PG_URL) {
  console.error('Missing PG_URL');
  process.exit(1);
}

const pool = new Pool({
  connectionString: PG_URL,
  // Keep pool small; Timescale is shared with heavy backfill jobs.
  max: Number(process.env.PG_POOL_MAX || 5),
});

app.get('/healthz', async (_req, res) => {
  try {
    const r = await pool.query('SELECT 1 as ok');
    res.json({ ok: true, db: r.rows?.[0]?.ok ?? 1 });
  } catch (e) {
    res.status(500).json({ ok: false, error: 'db_unreachable' });
  }
});

app.get('/candles', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.query.ticker || '').trim().toUpperCase();
  const tf = String(req.query.tf || '').trim();
  const beforeTs = req.query.beforeTs ? Number(req.query.beforeTs) : null;
  const limit = Math.min(Math.max(Number(req.query.limit || 500), 1), 2000);

  if (!ticker || !tf) return res.status(400).json({ ok: false, error: 'missing ticker/tf' });

  const params = [ticker, tf];
  let where = 'WHERE ticker = $1 AND tf = $2';
  if (beforeTs != null && Number.isFinite(beforeTs)) {
    // ts is stored as unix ms (BIGINT) — compare numerically.
    params.push(beforeTs);
    where += ` AND ts < $${params.length}`;
  }
  params.push(limit);

  const sql = `
SELECT ticker, tf,
  ts AS ts,  -- ts is stored as unix ms (BIGINT)
  o,h,l,c,v,source
FROM candles
${where}
ORDER BY ts DESC
LIMIT $${params.length}
  `.trim();

  try {
    const r = await pool.query(sql, params);
    const rows = (r.rows || []).map((x) => ({
      ts: Number(x.ts),
      o: x.o == null ? null : Number(x.o),
      h: x.h == null ? null : Number(x.h),
      l: x.l == null ? null : Number(x.l),
      c: x.c == null ? null : Number(x.c),
      v: x.v == null ? null : Number(x.v),
      source: x.source ?? null,
    }));

    res.json({ ok: true, ticker, tf, count: rows.length, rows });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/latest', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const tf = String(req.query.tf || '').trim();
  const limit = Math.min(Math.max(Number(req.query.limit || 500), 1), 2000);
  if (!tf) return res.status(400).json({ ok: false, error: 'missing tf' });

  const sql = `
SELECT ticker, tf, ts, o,h,l,c,v,source, ingested_at
FROM candles_latest
WHERE tf = $1
ORDER BY ticker
LIMIT $2
  `.trim();

  try {
    const r = await pool.query(sql, [tf, limit]);
    const rows = (r.rows || []).map((x) => ({
      ticker: String(x.ticker),
      tf: String(x.tf),
      ts: Number(x.ts),
      o: x.o == null ? null : Number(x.o),
      h: x.h == null ? null : Number(x.h),
      l: x.l == null ? null : Number(x.l),
      c: x.c == null ? null : Number(x.c),
      v: x.v == null ? null : Number(x.v),
      source: x.source ?? null,
      ingested_at: x.ingested_at ? String(x.ingested_at) : null,
    }));

    res.json({ ok: true, tf, count: rows.length, rows });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/top-movers', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const tf = String(req.query.tf || '').trim();
  const limit = Math.min(Math.max(Number(req.query.limit || 100), 1), 500);
  if (!tf) return res.status(400).json({ ok: false, error: 'missing tf' });

  // Compute percent change latest vs previous bar, using candles_latest + indexed back-lookup.
  const sql = `
WITH l AS (
  SELECT ticker, tf, ts, c
  FROM candles_latest
  WHERE tf = $1
)
SELECT
  l.ticker,
  l.tf,
  l.ts AS ts_latest,
  l.c  AS close_latest,
  p.c  AS close_prev,
  (l.c - p.c) / NULLIF(p.c, 0) AS pct_change
FROM l
JOIN LATERAL (
  SELECT c
  FROM candles
  WHERE ticker = l.ticker AND tf = l.tf AND ts < l.ts
  ORDER BY ts DESC
  LIMIT 1
) p ON true
ORDER BY pct_change DESC NULLS LAST
LIMIT $2
  `.trim();

  try {
    const r = await pool.query(sql, [tf, limit]);
    const rows = (r.rows || []).map((x) => ({
      ticker: String(x.ticker),
      tf: String(x.tf),
      ts_latest: Number(x.ts_latest),
      close_latest: x.close_latest == null ? null : Number(x.close_latest),
      close_prev: x.close_prev == null ? null : Number(x.close_prev),
      pct_change: x.pct_change == null ? null : Number(x.pct_change),
    }));

    res.json({ ok: true, tf, count: rows.length, rows });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// Fundamentals (Simplize → fi_latest)
app.get('/fundamentals/latest', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.query.ticker || '').trim().toUpperCase();
  const period = String(req.query.period || 'Q').trim().toUpperCase();
  const statement = String(req.query.statement || '').trim();
  const limit = Math.min(Math.max(Number(req.query.limit || 200), 1), 2000);

  if (!ticker) return res.status(400).json({ ok: false, error: 'missing ticker' });

  const params = [ticker, period];
  let where = 'WHERE ticker = $1 AND period = $2';
  if (statement) {
    params.push(statement);
    where += ` AND statement = $${params.length}`;
  }
  params.push(limit);

  const sql = `
SELECT ticker, period, statement, period_date, metric, value, fetched_at, ingested_at
FROM fi_latest
${where}
ORDER BY statement, metric
LIMIT $${params.length}
  `.trim();

  try {
    const r = await pool.query(sql, params);
    res.json({ ok: true, ticker, period, statement: statement || null, count: r.rows?.length || 0, rows: r.rows || [] });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/screener', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const metric = String(req.query.metric || '').trim();
  const period = String(req.query.period || 'Q').trim().toUpperCase();
  const statement = String(req.query.statement || '').trim();
  const minV = req.query.min != null ? Number(req.query.min) : null;
  const maxV = req.query.max != null ? Number(req.query.max) : null;
  const limit = Math.min(Math.max(Number(req.query.limit || 200), 1), 2000);

  if (!metric) return res.status(400).json({ ok: false, error: 'missing metric' });

  const params = [metric, period];
  let where = 'WHERE metric = $1 AND period = $2';
  if (statement) {
    params.push(statement);
    where += ` AND statement = $${params.length}`;
  }
  if (minV != null && Number.isFinite(minV)) {
    params.push(minV);
    where += ` AND value >= $${params.length}`;
  }
  if (maxV != null && Number.isFinite(maxV)) {
    params.push(maxV);
    where += ` AND value <= $${params.length}`;
  }
  params.push(limit);

  const sql = `
SELECT ticker, period, statement, period_date, metric, value
FROM fi_latest
${where}
ORDER BY value DESC NULLS LAST
LIMIT $${params.length}
  `.trim();

  try {
    const r = await pool.query(sql, params);
    res.json({ ok: true, metric, period, statement: statement || null, count: r.rows?.length || 0, rows: r.rows || [] });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`history-api listening on :${PORT}`);
});
