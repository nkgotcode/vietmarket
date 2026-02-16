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
  max: 10,
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
  if (beforeTs && Number.isFinite(beforeTs)) {
    params.push(new Date(beforeTs));
    where += ` AND ts < $${params.length}`;
  }
  params.push(limit);

  const sql = `
SELECT ticker, tf, (extract(epoch from ts) * 1000)::bigint AS ts, o,h,l,c,v,source
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

app.listen(PORT, '0.0.0.0', () => {
  console.log(`history-api listening on :${PORT}`);
});
