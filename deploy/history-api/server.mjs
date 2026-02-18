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

// News (Timescale-native; Option 2 strict: articles.text in Timescale)
app.get('/news/latest', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const limit = Math.min(Math.max(Number(req.query.limit || 50), 1), 200);
  const beforePublishedAt = req.query.beforePublishedAt ? String(req.query.beforePublishedAt) : null;
  const beforeUrl = req.query.beforeUrl ? String(req.query.beforeUrl) : null;

  const params = [limit];
  let where = "WHERE a.fetch_status = 'fetched'";

  // Keyset pagination on (published_at desc, url desc)
  if (beforePublishedAt && beforeUrl) {
    params.push(beforePublishedAt);
    params.push(beforeUrl);
    where += ` AND (a.published_at, a.url) < ($${params.length - 1}, $${params.length})`;
  } else if (beforePublishedAt) {
    params.push(beforePublishedAt);
    where += ` AND a.published_at < $${params.length}`;
  }

  const sql = `
SELECT
  a.url,
  a.title,
  a.source,
  a.published_at,
  left(coalesce(a.text,''), 220) as snippet,
  coalesce(array_agg(s.ticker) filter (where s.ticker is not null), '{}'::text[]) as tickers
FROM articles a
LEFT JOIN article_symbols s ON s.article_url = a.url
${where}
GROUP BY a.url, a.title, a.source, a.published_at, a.text
ORDER BY a.published_at DESC NULLS LAST, a.url DESC
LIMIT $1
  `.trim();

  try {
    const r = await pool.query(sql, params);
    const rows = (r.rows || []).map((x) => ({
      url: String(x.url),
      title: String(x.title),
      source: String(x.source),
      published_at: x.published_at ? String(x.published_at) : null,
      snippet: x.snippet ? String(x.snippet) : null,
      tickers: Array.isArray(x.tickers) ? x.tickers.map(String) : [],
    }));
    res.json({ ok: true, count: rows.length, rows, nextCursor: rows.length ? { beforePublishedAt: rows[rows.length - 1].published_at, beforeUrl: rows[rows.length - 1].url } : null });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/news/by-ticker', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.query.ticker || '').trim().toUpperCase();
  const limit = Math.min(Math.max(Number(req.query.limit || 50), 1), 200);
  const beforePublishedAt = req.query.beforePublishedAt ? String(req.query.beforePublishedAt) : null;
  const beforeUrl = req.query.beforeUrl ? String(req.query.beforeUrl) : null;

  if (!ticker) return res.status(400).json({ ok: false, error: 'missing ticker' });

  const params = [ticker, limit];
  let where = "WHERE s.ticker = $1 AND a.fetch_status = 'fetched'";

  if (beforePublishedAt && beforeUrl) {
    params.push(beforePublishedAt);
    params.push(beforeUrl);
    where += ` AND (a.published_at, a.url) < ($${params.length - 1}, $${params.length})`;
  } else if (beforePublishedAt) {
    params.push(beforePublishedAt);
    where += ` AND a.published_at < $${params.length}`;
  }

  const sql = `
SELECT
  a.url,
  a.title,
  a.source,
  a.published_at,
  left(coalesce(a.text,''), 220) as snippet
FROM article_symbols s
JOIN articles a ON a.url = s.article_url
${where}
ORDER BY a.published_at DESC NULLS LAST, a.url DESC
LIMIT $2
  `.trim();

  try {
    const r = await pool.query(sql, params);
    const rows = (r.rows || []).map((x) => ({
      url: String(x.url),
      title: String(x.title),
      source: String(x.source),
      published_at: x.published_at ? String(x.published_at) : null,
      snippet: x.snippet ? String(x.snippet) : null,
      tickers: [ticker],
    }));
    res.json({ ok: true, ticker, count: rows.length, rows, nextCursor: rows.length ? { beforePublishedAt: rows[rows.length - 1].published_at, beforeUrl: rows[rows.length - 1].url } : null });
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

app.get('/corporate-actions/latest', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const limit = Math.min(Math.max(Number(req.query.limit || 50), 1), 500);
  const beforeExDate = req.query.beforeExDate ? String(req.query.beforeExDate) : null; // YYYY-MM-DD
  const beforeId = req.query.beforeId ? String(req.query.beforeId) : null;

  const params = [];
  let where = 'WHERE ex_date IS NOT NULL';
  if (beforeExDate) {
    params.push(beforeExDate);
    where += ` AND (ex_date, id) < ($${params.length}::date, $${params.length + 1})`;
    params.push(beforeId || 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz');
  }
  params.push(limit);

  const sql = `
SELECT id, ticker, exchange, ex_date, record_date, pay_date, headline, event_type, source, source_url, ingested_at
FROM corporate_actions
${where}
ORDER BY ex_date DESC, id DESC
LIMIT $${params.length}
  `.trim();

  try {
    const r = await pool.query(sql, params);
    const rows = r.rows || [];
    const last = rows.length ? rows[rows.length - 1] : null;
    res.json({
      ok: true,
      count: rows.length,
      rows,
      nextCursor: last ? { beforeExDate: last.ex_date, beforeId: last.id } : null,
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/corporate-actions/by-ticker', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.query.ticker || '').trim().toUpperCase();
  const limit = Math.min(Math.max(Number(req.query.limit || 50), 1), 500);
  const beforeExDate = req.query.beforeExDate ? String(req.query.beforeExDate) : null; // YYYY-MM-DD
  const beforeId = req.query.beforeId ? String(req.query.beforeId) : null;

  if (!ticker) return res.status(400).json({ ok: false, error: 'missing ticker' });

  const params = [ticker];
  let where = 'WHERE ticker = $1 AND ex_date IS NOT NULL';
  if (beforeExDate) {
    params.push(beforeExDate);
    params.push(beforeId || 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz');
    where += ` AND (ex_date, id) < ($2::date, $3)`;
  }
  params.push(limit);

  const sql = `
SELECT id, ticker, exchange, ex_date, record_date, pay_date, headline, event_type, source, source_url, ingested_at
FROM corporate_actions
${where}
ORDER BY ex_date DESC, id DESC
LIMIT $${params.length}
  `.trim();

  try {
    const r = await pool.query(sql, params);
    const rows = r.rows || [];
    const last = rows.length ? rows[rows.length - 1] : null;
    res.json({
      ok: true,
      ticker,
      count: rows.length,
      rows,
      nextCursor: last ? { beforeExDate: last.ex_date, beforeId: last.id } : null,
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

function badRequest(res, code, message) {
  return res.status(400).json({ ok: false, error: code, message });
}

function parseWindowDays(raw, defaultDays = 7) {
  const n = raw == null ? defaultDays : Number(raw);
  if (!Number.isFinite(n) || n <= 0 || n > 90) return null;
  return Math.floor(n);
}

function parseLimit(raw, def, min, max) {
  const n = raw == null ? def : Number(raw);
  if (!Number.isFinite(n)) return null;
  return Math.min(Math.max(Math.floor(n), min), max);
}

// Versioned API (production contracts)
app.get('/v1/analytics/overview', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  try {
    const sql = `
WITH c AS (
  SELECT count(*)::bigint rows, count(distinct ticker)::int tickers, max(ts)::bigint max_ts, max(ingested_at) max_ingested_at
  FROM candles
), cov AS (
  SELECT
    max(case when metric='candles_eligible_total' then value_numeric end)::int eligible_total,
    max(case when metric='candles_eligible_with_candles' then value_numeric end)::int eligible_with,
    max(case when metric='candles_eligible_missing' then value_numeric end)::int eligible_missing,
    max(case when metric='candles_coverage_pct' then value_numeric end) coverage_pct
  FROM market_stats
), tf AS (
  SELECT
    count(*) FILTER (WHERE tf='1d')::bigint rows_1d,
    count(*) FILTER (WHERE tf='1h')::bigint rows_1h,
    count(*) FILTER (WHERE tf='15m')::bigint rows_15m,
    count(distinct ticker) FILTER (WHERE tf='1d')::int tickers_1d,
    count(distinct ticker) FILTER (WHERE tf='1h')::int tickers_1h,
    count(distinct ticker) FILTER (WHERE tf='15m')::int tickers_15m
  FROM candles
), ca AS (
  SELECT count(*)::int rows,
         count(*) FILTER (WHERE ex_date IS NOT NULL)::int ex_nonnull,
         count(*) FILTER (WHERE record_date IS NOT NULL)::int record_nonnull,
         count(*) FILTER (WHERE pay_date IS NOT NULL)::int pay_nonnull,
         max(ingested_at) as max_ingested_at
  FROM corporate_actions
), f AS (
  SELECT
    (select count(*)::bigint from financials) financials_rows,
    (select count(*)::bigint from fundamentals) fundamentals_rows,
    (select count(*)::bigint from technical_indicators) technical_rows,
    (select count(*)::bigint from indicators) indicators_rows,
    (select count(*)::bigint from market_stats) market_stats_rows
)
SELECT row_to_json(x) as j
FROM (
  SELECT
    now() as generated_at,
    c.rows as candles_rows,
    c.tickers as candles_tickers,
    c.max_ts as candles_max_ts,
    c.max_ingested_at as candles_max_ingested_at,
    tf.rows_1d, tf.rows_1h, tf.rows_15m,
    tf.tickers_1d, tf.tickers_1h, tf.tickers_15m,
    cov.eligible_total, cov.eligible_with, cov.eligible_missing, cov.coverage_pct,
    ca.rows as ca_rows, ca.ex_nonnull, ca.record_nonnull, ca.pay_nonnull, ca.max_ingested_at as ca_max_ingested_at,
    f.financials_rows, f.fundamentals_rows, f.technical_rows, f.indicators_rows, f.market_stats_rows,
    (SELECT value_text FROM market_stats WHERE metric='candles_frontier_status') as frontier_status,
    (SELECT value_numeric FROM market_stats WHERE metric='candles_frontier_lag_ms') as frontier_lag_ms
  FROM c, cov, tf, ca, f
) x
    `.trim();

    const r = await pool.query(sql);
    const j = r.rows?.[0]?.j || {};
    res.json({ ok: true, version: 'v1', data: j });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: 'internal_error', message: String(e?.message || e) });
  }
});

app.get('/v1/sentiment/overview', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const windowDays = parseWindowDays(req.query.windowDays, 7);
  const limit = parseLimit(req.query.limit, 30, 1, 200);
  if (windowDays == null) return badRequest(res, 'invalid_window_days', 'windowDays must be between 1 and 90');
  if (limit == null) return badRequest(res, 'invalid_limit', 'limit must be numeric');

  try {
    const sql = `
WITH recent AS (
  SELECT a.url, a.published_at, lower(coalesce(a.title,'') || ' ' || coalesce(a.text,'')) txt
  FROM articles a
  WHERE a.fetch_status='fetched'
    AND a.published_at >= now() - ($1::text || ' days')::interval
), scored AS (
  SELECT
    url,
    published_at,
    (
      (CASE WHEN txt ~ '(\\mbeat\\M|\\mgrowth\\M|\\mstrong\\M|\\mrally\\M|\\mprofit\\M|\\mupgrade\\M|\\mtích cực\\M|\\mtăng trưởng\\M|\\mlãi\\M|\\mkhả quan\\M)' THEN 1 ELSE 0 END)
      -
      (CASE WHEN txt ~ '(\\mmiss\\M|\\mweak\\M|\\mdrop\\M|\\mloss\\M|\\mdowngrade\\M|\\mrisk\\M|\\mtiêu cực\\M|\\mgiảm\\M|\\mlỗ\\M|\\mrủi ro\\M)' THEN 1 ELSE 0 END)
    )::int as score
  FROM recent
), ticker_scores AS (
  SELECT s.ticker,
         avg(sc.score)::double precision avg_score,
         count(*)::int articles,
         max(sc.published_at) last_article_at
  FROM scored sc
  JOIN article_symbols s ON s.article_url=sc.url
  GROUP BY s.ticker
), overall AS (
  SELECT avg(score)::double precision avg_score,
         count(*)::int articles,
         max(published_at) last_article_at
  FROM scored
)
SELECT json_build_object(
  'generated_at', now(),
  'window_days', $1::int,
  'overall', (SELECT row_to_json(o) FROM overall o),
  'top_positive', COALESCE((SELECT json_agg(row_to_json(t)) FROM (SELECT * FROM ticker_scores ORDER BY avg_score DESC NULLS LAST, articles DESC LIMIT $2) t), '[]'::json),
  'top_negative', COALESCE((SELECT json_agg(row_to_json(t)) FROM (SELECT * FROM ticker_scores ORDER BY avg_score ASC NULLS LAST, articles DESC LIMIT $2) t), '[]'::json)
) AS j
    `.trim();

    const r = await pool.query(sql, [windowDays, limit]);
    res.json({ ok: true, version: 'v1', data: r.rows?.[0]?.j || null });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: 'internal_error', message: String(e?.message || e) });
  }
});

app.get('/v1/sentiment/:ticker', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.params.ticker || '').trim().toUpperCase();
  const windowDays = parseWindowDays(req.query.windowDays, 30);
  if (!/^[A-Z0-9]{1,10}$/.test(ticker)) return badRequest(res, 'invalid_ticker', 'ticker is required');
  if (windowDays == null) return badRequest(res, 'invalid_window_days', 'windowDays must be between 1 and 90');

  try {
    const sql = `
WITH recent AS (
  SELECT a.url, a.published_at, a.title, left(coalesce(a.text,''),220) snippet,
         lower(coalesce(a.title,'') || ' ' || coalesce(a.text,'')) txt
  FROM article_symbols s
  JOIN articles a ON a.url=s.article_url
  WHERE s.ticker=$1
    AND a.fetch_status='fetched'
    AND a.published_at >= now() - ($2::text || ' days')::interval
), scored AS (
  SELECT *,
    (
      (CASE WHEN txt ~ '(\\mbeat\\M|\\mgrowth\\M|\\mstrong\\M|\\mrally\\M|\\mprofit\\M|\\mupgrade\\M|\\mtích cực\\M|\\mtăng trưởng\\M|\\mlãi\\M|\\mkhả quan\\M)' THEN 1 ELSE 0 END)
      -
      (CASE WHEN txt ~ '(\\mmiss\\M|\\mweak\\M|\\mdrop\\M|\\mloss\\M|\\mdowngrade\\M|\\mrisk\\M|\\mtiêu cực\\M|\\mgiảm\\M|\\mlỗ\\M|\\mrủi ro\\M)' THEN 1 ELSE 0 END)
    )::int as score
  FROM recent
)
SELECT json_build_object(
  'generated_at', now(),
  'ticker', $1,
  'window_days', $2::int,
  'summary', json_build_object(
    'avg_score', avg(score)::double precision,
    'articles', count(*)::int,
    'last_article_at', max(published_at)
  ),
  'recent_articles', COALESCE(json_agg(json_build_object('url',url,'title',title,'published_at',published_at,'score',score,'snippet',snippet) ORDER BY published_at DESC) FILTER (WHERE url IS NOT NULL), '[]'::json)
) AS j
FROM scored
    `.trim();

    const r = await pool.query(sql, [ticker, windowDays]);
    res.json({ ok: true, version: 'v1', data: r.rows?.[0]?.j || null });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: 'internal_error', message: String(e?.message || e) });
  }
});

app.get('/v1/context/:ticker', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  const ticker = String(req.params.ticker || '').trim().toUpperCase();
  if (!/^[A-Z0-9]{1,10}$/.test(ticker)) return badRequest(res, 'invalid_ticker', 'ticker is required');

  try {
    const sql = `
WITH c AS (
  SELECT tf, ts, o,h,l,c,v,source, ingested_at
  FROM candles_latest
  WHERE ticker=$1 AND tf IN ('1d','1h','15m')
), t AS (
  SELECT ticker, tf, asof_ts, close, sma20, sma50, ema20, updated_at
  FROM technical_indicators
  WHERE ticker=$1
), f AS (
  SELECT metric, value, period, period_date, updated_at
  FROM fundamentals
  WHERE ticker=$1
), ca AS (
  SELECT id, ex_date, record_date, pay_date, headline, event_type, source, source_url, ingested_at
  FROM corporate_actions
  WHERE ticker=$1
  ORDER BY ex_date DESC NULLS LAST, id DESC
  LIMIT 20
), n AS (
  SELECT a.url, a.title, a.source, a.published_at, left(coalesce(a.text,''),220) snippet
  FROM article_symbols s
  JOIN articles a ON a.url=s.article_url
  WHERE s.ticker=$1 AND a.fetch_status='fetched'
  ORDER BY a.published_at DESC NULLS LAST, a.url DESC
  LIMIT 20
)
SELECT json_build_object(
  'generated_at', now(),
  'ticker', $1,
  'candles_latest', COALESCE((SELECT json_object_agg(tf, row_to_json(cx)) FROM (SELECT * FROM c) cx), '{}'::json),
  'technicals', COALESCE((SELECT json_object_agg(tf, row_to_json(tx)) FROM (SELECT * FROM t) tx), '{}'::json),
  'fundamentals', COALESCE((SELECT json_agg(row_to_json(fx)) FROM (SELECT * FROM f) fx), '[]'::json),
  'corporate_actions', COALESCE((SELECT json_agg(row_to_json(cax)) FROM (SELECT * FROM ca) cax), '[]'::json),
  'news', COALESCE((SELECT json_agg(row_to_json(nx)) FROM (SELECT * FROM n) nx), '[]'::json)
) AS j
    `.trim();

    const r = await pool.query(sql, [ticker]);
    res.json({ ok: true, version: 'v1', data: r.rows?.[0]?.j || null });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: 'internal_error', message: String(e?.message || e) });
  }
});

app.get('/v1/overall/health', async (req, res) => {
  if (!authOk(req)) return res.status(401).json({ ok: false, error: 'unauthorized' });

  try {
    const sql = `
WITH c AS (
  SELECT count(*)::bigint rows, max(ts)::bigint max_ts, max(ingested_at) max_ingested_at FROM candles
), s AS (
  SELECT count(*)::int rows, max(updated_at) max_updated_at FROM symbols
), rq AS (
  SELECT
    count(*) FILTER (WHERE status='queued')::int queued,
    count(*) FILTER (WHERE status='running')::int running,
    count(*) FILTER (WHERE status='done')::int done
  FROM candle_repair_queue
), cov AS (
  SELECT
    max(case when metric='candles_eligible_total' then value_numeric end)::int eligible_total,
    max(case when metric='candles_eligible_with_candles' then value_numeric end)::int eligible_with,
    max(case when metric='candles_eligible_missing' then value_numeric end)::int eligible_missing
  FROM market_stats
)
SELECT json_build_object(
  'generated_at', now(),
  'candles', json_build_object('rows', c.rows, 'max_ts', c.max_ts, 'max_ingested_at', c.max_ingested_at),
  'symbols', json_build_object('rows', s.rows, 'max_updated_at', s.max_updated_at),
  'coverage', json_build_object('eligible_total', cov.eligible_total, 'eligible_with', cov.eligible_with, 'eligible_missing', cov.eligible_missing),
  'repair_queue', json_build_object('queued', rq.queued, 'running', rq.running, 'done', rq.done),
  'frontier', json_build_object(
     'status', (SELECT value_text FROM market_stats WHERE metric='candles_frontier_status'),
     'lag_ms', (SELECT value_numeric FROM market_stats WHERE metric='candles_frontier_lag_ms')
  )
) AS j
FROM c,s,rq,cov
    `.trim();

    const r = await pool.query(sql);
    res.json({ ok: true, version: 'v1', data: r.rows?.[0]?.j || null });
  } catch (e) {
    console.error(e);
    res.status(500).json({ ok: false, error: 'internal_error', message: String(e?.message || e) });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`history-api listening on :${PORT}`);
});
