#!/usr/bin/env python3
"""Build and sync derived market/news/fundamental tables in Timescale/Postgres.

Creates and maintains:
- market_stats
- financials
- fundamentals
- technical_indicators
- indicators
- article_symbols (news ↔ ticker links)

Sources:
- candles
- fi_latest
- articles
- symbols
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import psycopg2
import numpy as np
import talib
from psycopg2.extras import execute_values


def pg_url() -> str:
    u = os.environ.get("PG_URL")
    if not u:
        raise RuntimeError("Missing PG_URL")
    return u


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


DDL = """
CREATE TABLE IF NOT EXISTS market_stats (
  metric text PRIMARY KEY,
  value_numeric double precision,
  value_text text,
  asof_ts bigint,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financials (
  ticker text NOT NULL,
  period text NOT NULL,
  statement text NOT NULL,
  period_date date,
  metric text NOT NULL,
  value double precision,
  source text NOT NULL DEFAULT 'fi_latest',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period, statement, metric)
);

CREATE TABLE IF NOT EXISTS fundamentals (
  ticker text NOT NULL,
  metric text NOT NULL,
  value double precision,
  period text,
  period_date date,
  source text NOT NULL DEFAULT 'financials',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, metric)
);

CREATE TABLE IF NOT EXISTS technical_indicators (
  ticker text NOT NULL,
  tf text NOT NULL,
  asof_ts bigint NOT NULL,
  close double precision,
  sma20 double precision,
  sma50 double precision,
  ema20 double precision,
  rsi14 double precision,
  macd double precision,
  macd_signal double precision,
  macd_hist double precision,
  atr14 double precision,
  bb_mid double precision,
  bb_upper double precision,
  bb_lower double precision,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, tf)
);

CREATE TABLE IF NOT EXISTS indicators (
  ticker text NOT NULL,
  tf text NOT NULL,
  indicator text NOT NULL,
  value double precision,
  asof_ts bigint NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, tf, indicator)
);
"""


DDL_TECHNICAL_ADD_COLS = """
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS rsi14 double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS macd double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS macd_signal double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS macd_hist double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS atr14 double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_mid double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_upper double precision;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_lower double precision;
"""


SQL_FINANCIALS = """
INSERT INTO financials (ticker, period, statement, period_date, metric, value, source, updated_at)
SELECT ticker, period, statement, period_date, metric, value, 'fi_latest', now()
FROM fi_latest
ON CONFLICT (ticker, period, statement, metric) DO UPDATE SET
  period_date = EXCLUDED.period_date,
  value = EXCLUDED.value,
  source = EXCLUDED.source,
  updated_at = now();
"""


SQL_FUNDAMENTALS = """
WITH ranked AS (
  SELECT ticker, metric, value, period, period_date,
         row_number() OVER (
           PARTITION BY ticker, metric
           ORDER BY period_date DESC NULLS LAST,
                    CASE WHEN period='Q' THEN 1 WHEN period='Y' THEN 2 ELSE 3 END
         ) AS rn
  FROM financials
)
INSERT INTO fundamentals (ticker, metric, value, period, period_date, source, updated_at)
SELECT ticker, metric, value, period, period_date, 'financials', now()
FROM ranked WHERE rn=1
ON CONFLICT (ticker, metric) DO UPDATE SET
  value = EXCLUDED.value,
  period = EXCLUDED.period,
  period_date = EXCLUDED.period_date,
  source = EXCLUDED.source,
  updated_at = now();
"""


SQL_TECHNICAL = """
WITH pairs AS (
  SELECT DISTINCT ticker, tf
  FROM candles
  WHERE tf IN ('15m','1h','1d')
), sampled AS (
  SELECT p.ticker, p.tf, x.ts, x.o, x.h, x.l, x.c
  FROM pairs p
  CROSS JOIN LATERAL (
    SELECT ts, o, h, l, c
    FROM candles c
    WHERE c.ticker = p.ticker AND c.tf = p.tf
    ORDER BY ts DESC
    LIMIT 140
  ) x
), base0 AS (
  SELECT ticker, tf, ts, o, h, l, c,
         row_number() OVER (PARTITION BY ticker, tf ORDER BY ts DESC) AS rn_desc,
         lag(c) OVER (PARTITION BY ticker, tf ORDER BY ts) AS prev_close
  FROM sampled
), base AS (
  SELECT
    ticker, tf, ts, c, rn_desc, prev_close,
    avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma20,
    avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma50,
    avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS sma12,
    avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 25 PRECEDING AND CURRENT ROW) AS sma26,
    stddev_samp(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS std20,

    avg(GREATEST(c - COALESCE(prev_close, c), 0.0)) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_gain14,
    avg(ABS(LEAST(c - COALESCE(prev_close, c), 0.0))) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_loss14,
    avg(GREATEST(h - l, ABS(h - COALESCE(prev_close, c)), ABS(l - COALESCE(prev_close, c)))) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS atr14,

    2.0/(20+1) AS alpha20,
    2.0/(12+1) AS alpha12,
    2.0/(26+1) AS alpha26
  FROM base0
), enriched AS (
  SELECT
    ticker, tf, ts, rn_desc,
    c AS close,
    sma20, sma50,
    (c * alpha20 + COALESCE(sma20, c) * (1-alpha20)) AS ema20,
    CASE WHEN avg_loss14 IS NULL OR avg_loss14 = 0 THEN NULL
         ELSE 100.0 - (100.0 / (1.0 + (avg_gain14 / avg_loss14))) END AS rsi14,
    (c * alpha12 + COALESCE(sma12, c) * (1-alpha12))
      - (c * alpha26 + COALESCE(sma26, c) * (1-alpha26)) AS macd,
    atr14,
    sma20 AS bb_mid,
    (sma20 + 2.0 * std20) AS bb_upper,
    (sma20 - 2.0 * std20) AS bb_lower
  FROM base
), macd_sig AS (
  SELECT
    ticker, tf, ts, rn_desc,
    close, sma20, sma50, ema20,
    rsi14, macd,
    avg(macd) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 8 PRECEDING AND CURRENT ROW) AS macd_signal,
    atr14, bb_mid, bb_upper, bb_lower
  FROM enriched
), latest AS (
  SELECT
    ticker, tf, ts AS asof_ts,
    close, sma20, sma50, ema20,
    rsi14, macd, macd_signal, (macd - macd_signal) AS macd_hist,
    atr14, bb_mid, bb_upper, bb_lower
  FROM macd_sig
  WHERE rn_desc = 1
)
INSERT INTO technical_indicators (
  ticker, tf, asof_ts,
  close, sma20, sma50, ema20,
  rsi14, macd, macd_signal, macd_hist,
  atr14, bb_mid, bb_upper, bb_lower,
  updated_at
)
SELECT
  ticker, tf, asof_ts,
  close, sma20, sma50, ema20,
  rsi14, macd, macd_signal, macd_hist,
  atr14, bb_mid, bb_upper, bb_lower,
  now()
FROM latest
ON CONFLICT (ticker, tf) DO UPDATE SET
  asof_ts = EXCLUDED.asof_ts,
  close = EXCLUDED.close,
  sma20 = EXCLUDED.sma20,
  sma50 = EXCLUDED.sma50,
  ema20 = EXCLUDED.ema20,
  rsi14 = EXCLUDED.rsi14,
  macd = EXCLUDED.macd,
  macd_signal = EXCLUDED.macd_signal,
  macd_hist = EXCLUDED.macd_hist,
  atr14 = EXCLUDED.atr14,
  bb_mid = EXCLUDED.bb_mid,
  bb_upper = EXCLUDED.bb_upper,
  bb_lower = EXCLUDED.bb_lower,
  updated_at = now();
"""


SQL_INDICATORS = """
WITH src AS (
  SELECT ticker, tf, asof_ts,
         close, sma20, sma50, ema20,
         rsi14, macd, macd_signal, macd_hist,
         atr14, bb_mid, bb_upper, bb_lower
  FROM technical_indicators
)
INSERT INTO indicators (ticker, tf, indicator, value, asof_ts, updated_at)
SELECT ticker, tf, indicator, value, asof_ts, now()
FROM src
CROSS JOIN LATERAL (
  VALUES
    ('close', close),
    ('sma20', sma20),
    ('sma50', sma50),
    ('ema20', ema20),
    ('rsi14', rsi14),
    ('macd', macd),
    ('macd_signal', macd_signal),
    ('macd_hist', macd_hist),
    ('atr14', atr14),
    ('bb_mid', bb_mid),
    ('bb_upper', bb_upper),
    ('bb_lower', bb_lower)
) v(indicator, value)
ON CONFLICT (ticker, tf, indicator) DO UPDATE SET
  value = EXCLUDED.value,
  asof_ts = EXCLUDED.asof_ts,
  updated_at = now();
"""


SQL_MARKET_STATS = """
WITH c AS (
  SELECT count(*)::double precision AS total_rows,
         count(distinct ticker)::double precision AS total_tickers,
         max(ts) AS max_ts,
         max(ingested_at) AS max_ingested_at
  FROM candles
), ca AS (
  SELECT count(*)::double precision AS ca_rows,
         count(*) FILTER (WHERE ex_date IS NOT NULL)::double precision AS ca_ex,
         count(*) FILTER (WHERE record_date IS NOT NULL)::double precision AS ca_record,
         count(*) FILTER (WHERE pay_date IS NOT NULL)::double precision AS ca_pay
  FROM corporate_actions
), eligible AS (
  SELECT ticker
  FROM symbols
  WHERE coalesce(active,true)=true
    AND ticker ~ '^[A-Z0-9]{3,4}$'
    AND ticker NOT IN ('VNINDEX','HNXINDEX','UPCOMINDEX')
), cov AS (
  SELECT
    (SELECT count(*)::double precision FROM eligible) AS eligible_total,
    (SELECT count(distinct c.ticker)::double precision FROM candles c JOIN eligible e ON e.ticker=c.ticker) AS eligible_with_candles,
    (SELECT count(*)::double precision FROM eligible e LEFT JOIN (SELECT distinct ticker FROM candles) c ON c.ticker=e.ticker WHERE c.ticker IS NULL) AS eligible_missing
), tf AS (
  SELECT
    count(distinct ticker) FILTER (WHERE tf='1d')::double precision AS tf_1d_tickers,
    count(distinct ticker) FILTER (WHERE tf='1h')::double precision AS tf_1h_tickers,
    count(distinct ticker) FILTER (WHERE tf='15m')::double precision AS tf_15m_tickers,
    count(*) FILTER (WHERE tf='1d')::double precision AS tf_1d_rows,
    count(*) FILTER (WHERE tf='1h')::double precision AS tf_1h_rows,
    count(*) FILTER (WHERE tf='15m')::double precision AS tf_15m_rows
  FROM candles
), q AS (
  SELECT
    count(*) FILTER (WHERE status = 'queued')::double precision AS queue_queued,
    count(*) FILTER (WHERE status = 'running')::double precision AS queue_running,
    count(*) FILTER (WHERE status = 'done')::double precision AS queue_done,
    count(*) FILTER (WHERE status = 'queued' AND created_at >= now() - interval '1 hour')::double precision AS queue_queued_1h,
    count(*) FILTER (WHERE status = 'queued' AND created_at >= now() - interval '24 hour')::double precision AS queue_queued_24h,
    count(*) FILTER (WHERE status = 'done' AND updated_at >= now() - interval '1 hour')::double precision AS queue_done_1h,
    count(*) FILTER (WHERE status = 'done' AND updated_at >= now() - interval '24 hour')::double precision AS queue_done_24h
  FROM candle_repair_queue
), a AS (
  SELECT
    count(*)::double precision AS articles_total,
    count(*) FILTER (WHERE fetch_status = 'fetched')::double precision AS articles_fetched_total,
    count(*) FILTER (WHERE convex_text_file_id IS NOT NULL AND convex_text_file_id <> '')::double precision AS articles_convex_linked_total,
    count(*) FILTER (WHERE convex_text_sha256 IS NOT NULL AND convex_text_sha256 <> '')::double precision AS articles_convex_sha_total
  FROM articles
), asy AS (
  SELECT count(*)::double precision AS article_symbols_rows
  FROM article_symbols
), diag AS (
  SELECT
    CASE
      WHEN c.max_ts IS NULL THEN 'unknown'
      WHEN (extract(epoch from now())*1000 - c.max_ts) <= 7200000 THEN 'fresh'
      WHEN c.max_ingested_at >= (now() - interval '30 minutes') THEN 'market_closed_or_source_limited'
      ELSE 'pipeline_stalled'
    END AS frontier_status,
    GREATEST(0, (extract(epoch from now())*1000 - c.max_ts))::double precision AS frontier_lag_ms
  FROM c
)
INSERT INTO market_stats(metric, value_numeric, value_text, asof_ts, updated_at)
SELECT * FROM (
  SELECT 'candles_total_rows', c.total_rows, NULL::text, c.max_ts, now() FROM c
  UNION ALL SELECT 'candles_total_tickers', c.total_tickers, NULL::text, c.max_ts, now() FROM c
  UNION ALL SELECT 'candles_max_ts', c.max_ts::double precision, NULL::text, c.max_ts, now() FROM c
  UNION ALL SELECT 'candles_max_ingested_at', NULL::double precision, c.max_ingested_at::text, c.max_ts, now() FROM c
  UNION ALL SELECT 'candles_frontier_status', NULL::double precision, d.frontier_status, c.max_ts, now() FROM c, diag d
  UNION ALL SELECT 'candles_frontier_lag_ms', d.frontier_lag_ms, NULL::text, c.max_ts, now() FROM c, diag d

  UNION ALL SELECT 'candles_eligible_total', cov.eligible_total, NULL::text, c.max_ts, now() FROM cov,c
  UNION ALL SELECT 'candles_eligible_with_candles', cov.eligible_with_candles, NULL::text, c.max_ts, now() FROM cov,c
  UNION ALL SELECT 'candles_eligible_missing', cov.eligible_missing, NULL::text, c.max_ts, now() FROM cov,c
  UNION ALL SELECT 'candles_coverage_pct', CASE WHEN cov.eligible_total > 0 THEN ((cov.eligible_with_candles/cov.eligible_total)*100.0) ELSE NULL END, NULL::text, c.max_ts, now() FROM cov,c

  UNION ALL SELECT 'candles_1d_tickers', tf.tf_1d_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1h_tickers', tf.tf_1h_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_15m_tickers', tf.tf_15m_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1d_rows', tf.tf_1d_rows, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1h_rows', tf.tf_1h_rows, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_15m_rows', tf.tf_15m_rows, NULL::text, c.max_ts, now() FROM tf,c

  UNION ALL SELECT 'repair_queue_queued', q.queue_queued, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_running', q.queue_running, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_done', q.queue_done, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_queued_1h', q.queue_queued_1h, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_queued_24h', q.queue_queued_24h, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_done_1h', q.queue_done_1h, NULL::text, c.max_ts, now() FROM q,c
  UNION ALL SELECT 'repair_queue_done_24h', q.queue_done_24h, NULL::text, c.max_ts, now() FROM q,c

  UNION ALL SELECT 'articles_total', a.articles_total, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'articles_fetched_total', a.articles_fetched_total, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'articles_convex_linked_total', a.articles_convex_linked_total, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'articles_convex_sha_total', a.articles_convex_sha_total, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'articles_fetch_coverage_pct', CASE WHEN a.articles_total > 0 THEN (a.articles_fetched_total/a.articles_total)*100.0 ELSE NULL END, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'articles_convex_link_coverage_pct', CASE WHEN a.articles_fetched_total > 0 THEN (a.articles_convex_linked_total/a.articles_fetched_total)*100.0 ELSE NULL END, NULL::text, c.max_ts, now() FROM a,c
  UNION ALL SELECT 'article_symbols_rows', asy.article_symbols_rows, NULL::text, c.max_ts, now() FROM asy,c

  UNION ALL SELECT 'ca_total_rows', ca.ca_rows, NULL::text, (SELECT max_ts FROM c), now() FROM ca
  UNION ALL SELECT 'ca_ex_nonnull', ca.ca_ex, NULL::text, (SELECT max_ts FROM c), now() FROM ca
  UNION ALL SELECT 'ca_record_nonnull', ca.ca_record, NULL::text, (SELECT max_ts FROM c), now() FROM ca
  UNION ALL SELECT 'ca_pay_nonnull', ca.ca_pay, NULL::text, (SELECT max_ts FROM c), now() FROM ca
) s(metric, value_numeric, value_text, asof_ts, updated_at)
ON CONFLICT (metric) DO UPDATE SET
  value_numeric = EXCLUDED.value_numeric,
  value_text = EXCLUDED.value_text,
  asof_ts = EXCLUDED.asof_ts,
  updated_at = now();
"""


STOPWORDS = {
    "ETF", "USD", "VND", "VNINDEX", "HNX", "HOSE", "UPCOM", "CTCP", "VNI",
}

RX_PAREN = re.compile(r"\(([A-Z0-9]{2,5})\)")
RX_EXCH_PAREN = re.compile(r"\b([A-Z0-9]{2,5})\s*\((HOSE|HNX|UPCOM)\)\b")
RX_EXCH_COLON = re.compile(r"\b(HOSE|HNX|UPCOM)\s*[:\-]\s*([A-Z0-9]{2,5})\b")
RX_KEYWORD = re.compile(r"(?:CỔ\s*PHIẾU|MÃ\s*(?:CK\s*)?|MÃ\s*CHỨNG\s*KHOÁN\s*)([A-Z0-9]{2,5})")
RX_TOKEN = re.compile(r"\b([A-Z0-9]{2,5})\b")


def _valid_ticker(tk: str, known: set[str]) -> bool:
    return bool(re.match(r"^[A-Z0-9]{2,5}$", tk)) and tk in known and tk not in STOPWORDS


def _add_hit(hits: dict[str, tuple[float, str]], ticker: str, confidence: float, method: str):
    prev = hits.get(ticker)
    if prev is None or confidence > prev[0]:
        hits[ticker] = (confidence, method)


def link_symbols(title: str | None, text: str | None, known: set[str]) -> list[tuple[str, float, str]]:
    title_up = (title or "").upper()
    body_up = (text or "").upper()
    body_up = body_up[:8000]
    hits: dict[str, tuple[float, str]] = {}

    for m in RX_PAREN.finditer(title_up):
        tk = m.group(1)
        if _valid_ticker(tk, known):
            _add_hit(hits, tk, 0.95, "title_paren")

    for m in RX_EXCH_PAREN.finditer(title_up):
        tk = m.group(1)
        if _valid_ticker(tk, known):
            _add_hit(hits, tk, 0.92, "title_exchange_paren")

    for m in RX_EXCH_COLON.finditer(title_up):
        tk = m.group(2)
        if _valid_ticker(tk, known):
            _add_hit(hits, tk, 0.92, "title_exchange_colon")

    for m in RX_KEYWORD.finditer(title_up + " " + body_up):
        tk = m.group(1)
        if _valid_ticker(tk, known):
            _add_hit(hits, tk, 0.90, "keyword")

    # fallback token pass on title only to reduce false positives
    for m in RX_TOKEN.finditer(title_up):
        tk = m.group(1)
        if _valid_ticker(tk, known):
            _add_hit(hits, tk, 0.60, "title_token")

    return [(tk, c, method) for tk, (c, method) in sorted(hits.items(), key=lambda x: (-x[1][0], x[0]))]


def sync_article_symbols(cur, *, batch_size: int = 1000) -> dict:
    cur.execute("SELECT ticker FROM symbols WHERE coalesce(active,true)=true")
    known = {r[0] for r in cur.fetchall() if r[0]}

    cur.execute(
        """
        SELECT url, title, text
        FROM articles
        WHERE fetch_status='fetched'
        ORDER BY discovered_at DESC NULLS LAST, ingested_at DESC NULLS LAST
        LIMIT %s
        """,
        (int(os.environ.get("ARTICLE_SYMBOLS_BACKFILL_LIMIT", "50000")),),
    )
    rows = cur.fetchall()

    payload: list[tuple[str, str, float, str]] = []
    article_count = 0
    linked_count = 0
    for url, title, text in rows:
        article_count += 1
        links = link_symbols(title, text, known)
        if not links:
            continue
        linked_count += 1
        for tk, conf, method in links:
            payload.append((url, tk, conf, method))

    if payload:
        execute_values(
            cur,
            """
            INSERT INTO article_symbols (article_url, ticker, confidence, method)
            VALUES %s
            ON CONFLICT (article_url, ticker) DO UPDATE SET
              confidence = GREATEST(article_symbols.confidence, EXCLUDED.confidence),
              method = CASE
                WHEN EXCLUDED.confidence >= article_symbols.confidence THEN EXCLUDED.method
                ELSE article_symbols.method
              END
            """,
            payload,
            page_size=batch_size,
        )

    return {
        "article_rows_scanned": article_count,
        "articles_with_links": linked_count,
        "article_symbol_upserts": len(payload),
    }



def apply_talib_indicators(cur, lookback: int = 300) -> dict:
    """Recompute technical indicators with TA-Lib and upsert latest per (ticker, tf)."""
    cur.execute("""
      SELECT DISTINCT ticker, tf
      FROM candles
      WHERE tf IN ('15m','1h','1d')
    """)
    pairs = cur.fetchall()

    updates = []
    for ticker, tf in pairs:
        cur.execute("""
          SELECT ts, o, h, l, c
          FROM candles
          WHERE ticker=%s AND tf=%s
          ORDER BY ts DESC
          LIMIT %s
        """, (ticker, tf, lookback))
        rows = cur.fetchall()
        if not rows:
            continue
        rows = list(reversed(rows))

        ts = np.array([r[0] for r in rows], dtype=np.int64)
        o = np.array([float(r[1]) for r in rows], dtype=np.float64)
        h = np.array([float(r[2]) for r in rows], dtype=np.float64)
        l = np.array([float(r[3]) for r in rows], dtype=np.float64)
        c = np.array([float(r[4]) for r in rows], dtype=np.float64)

        sma20 = talib.SMA(c, timeperiod=20)
        sma50 = talib.SMA(c, timeperiod=50)
        ema20 = talib.EMA(c, timeperiod=20)
        rsi14 = talib.RSI(c, timeperiod=14)
        macd, macd_signal, macd_hist = talib.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)
        atr14 = talib.ATR(h, l, c, timeperiod=14)
        bb_upper, bb_mid, bb_lower = talib.BBANDS(c, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

        i = len(c) - 1

        def v(arr):
            x = arr[i]
            if x is None:
                return None
            if isinstance(x, (float, np.floating)) and np.isnan(x):
                return None
            return float(x)

        updates.append((
            ticker, tf, int(ts[i]), float(c[i]),
            v(sma20), v(sma50), v(ema20),
            v(rsi14), v(macd), v(macd_signal), v(macd_hist),
            v(atr14), v(bb_mid), v(bb_upper), v(bb_lower),
        ))

    if updates:
        execute_values(
            cur,
            """
            INSERT INTO technical_indicators (
              ticker, tf, asof_ts,
              close, sma20, sma50, ema20,
              rsi14, macd, macd_signal, macd_hist,
              atr14, bb_mid, bb_upper, bb_lower,
              updated_at
            ) VALUES %s
            ON CONFLICT (ticker, tf) DO UPDATE SET
              asof_ts = EXCLUDED.asof_ts,
              close = EXCLUDED.close,
              sma20 = EXCLUDED.sma20,
              sma50 = EXCLUDED.sma50,
              ema20 = EXCLUDED.ema20,
              rsi14 = EXCLUDED.rsi14,
              macd = EXCLUDED.macd,
              macd_signal = EXCLUDED.macd_signal,
              macd_hist = EXCLUDED.macd_hist,
              atr14 = EXCLUDED.atr14,
              bb_mid = EXCLUDED.bb_mid,
              bb_upper = EXCLUDED.bb_upper,
              bb_lower = EXCLUDED.bb_lower,
              updated_at = now()
            """,
            [u + () for u in updates],
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())",
            page_size=500,
        )

    return {"talib_pairs": len(pairs), "talib_updates": len(updates)}


def main() -> int:
    out = {"ok": True, "at": now_iso()}
    with psycopg2.connect(pg_url()) as pg:
        with pg.cursor() as cur:
            cur.execute(DDL)
            cur.execute(DDL_TECHNICAL_ADD_COLS)

            cur.execute(SQL_FINANCIALS)
            out["financials_sync"] = cur.rowcount

            cur.execute(SQL_FUNDAMENTALS)
            out["fundamentals_sync"] = cur.rowcount

            cur.execute(SQL_TECHNICAL)
            out["technical_sync"] = cur.rowcount

            out.update(apply_talib_indicators(cur))

            cur.execute(SQL_INDICATORS)
            out["indicators_sync"] = cur.rowcount

            out.update(sync_article_symbols(cur))

            cur.execute(SQL_MARKET_STATS)
            out["market_stats_sync"] = cur.rowcount

            cur.execute("select count(*) from financials")
            out["financials_rows"] = cur.fetchone()[0]
            cur.execute("select count(*) from fundamentals")
            out["fundamentals_rows"] = cur.fetchone()[0]
            cur.execute("select count(*) from technical_indicators")
            out["technical_indicators_rows"] = cur.fetchone()[0]
            cur.execute("select count(*) from indicators")
            out["indicators_rows"] = cur.fetchone()[0]
            cur.execute("select count(*) from article_symbols")
            out["article_symbols_rows"] = cur.fetchone()[0]
            cur.execute("select count(*) from market_stats")
            out["market_stats_rows"] = cur.fetchone()[0]

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
