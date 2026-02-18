#!/usr/bin/env python3
"""Build and sync derived market/fundamental tables in Timescale/Postgres.

Creates and maintains:
- market_stats
- financials
- fundamentals
- technical_indicators
- indicators

Sources:
- candles
- fi_latest
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import psycopg2


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
WITH base AS (
  SELECT ticker, tf, ts, c,
         row_number() OVER (PARTITION BY ticker, tf ORDER BY ts DESC) AS rn_desc,
         avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma20,
         avg(c) OVER (PARTITION BY ticker, tf ORDER BY ts ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma50,
         2.0/(20+1) AS alpha
  FROM candles
  WHERE tf IN ('15m','1h','1d')
), latest AS (
  SELECT ticker, tf, ts AS asof_ts, c AS close, sma20, sma50
  FROM base
  WHERE rn_desc = 1
)
INSERT INTO technical_indicators (ticker, tf, asof_ts, close, sma20, sma50, ema20, updated_at)
SELECT ticker, tf, asof_ts, close, sma20, sma50,
       (close * alpha + COALESCE(sma20, close) * (1-alpha)) AS ema20,
       now()
FROM (
  SELECT l.*, 2.0/(20+1) AS alpha FROM latest l
) s
ON CONFLICT (ticker, tf) DO UPDATE SET
  asof_ts = EXCLUDED.asof_ts,
  close = EXCLUDED.close,
  sma20 = EXCLUDED.sma20,
  sma50 = EXCLUDED.sma50,
  ema20 = EXCLUDED.ema20,
  updated_at = now();
"""


SQL_INDICATORS = """
WITH src AS (
  SELECT ticker, tf, asof_ts, close, sma20, sma50, ema20
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
    ('ema20', ema20)
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
  UNION ALL SELECT 'candles_coverage_pct', CASE WHEN cov.eligible_total > 0 THEN round((cov.eligible_with_candles/cov.eligible_total)*100.0,2) ELSE NULL END, NULL::text, c.max_ts, now() FROM cov,c

  UNION ALL SELECT 'candles_1d_tickers', tf.tf_1d_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1h_tickers', tf.tf_1h_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_15m_tickers', tf.tf_15m_tickers, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1d_rows', tf.tf_1d_rows, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_1h_rows', tf.tf_1h_rows, NULL::text, c.max_ts, now() FROM tf,c
  UNION ALL SELECT 'candles_15m_rows', tf.tf_15m_rows, NULL::text, c.max_ts, now() FROM tf,c

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


def main() -> int:
    out = {"ok": True, "at": now_iso()}
    with psycopg2.connect(pg_url()) as pg:
        with pg.cursor() as cur:
            cur.execute(DDL)
            cur.execute(SQL_FINANCIALS)
            out["financials_sync"] = cur.rowcount
            cur.execute(SQL_FUNDAMENTALS)
            out["fundamentals_sync"] = cur.rowcount
            cur.execute(SQL_TECHNICAL)
            out["technical_sync"] = cur.rowcount
            cur.execute(SQL_INDICATORS)
            out["indicators_sync"] = cur.rowcount
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
            cur.execute("select count(*) from market_stats")
            out["market_stats_rows"] = cur.fetchone()[0]

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
