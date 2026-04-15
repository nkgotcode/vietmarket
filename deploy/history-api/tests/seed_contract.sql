-- Core symbols
INSERT INTO symbols (ticker, name, exchange, active, updated_at)
VALUES ('VCB', 'VCB', 'HOSE', true, (extract(epoch from now())*1000)::bigint)
ON CONFLICT (ticker) DO UPDATE SET updated_at = EXCLUDED.updated_at;

-- Candles + latest snapshot
INSERT INTO candles (ticker, tf, ts, o, h, l, c, v, source, ingested_at)
VALUES
  ('VCB','1d',1700000000000,90,95,89,94,1000,'seed',now()),
  ('VCB','1d',1700086400000,94,96,93,95,1200,'seed',now()),
  ('VCB','1h',1700086400000,94,95,93,94.5,100,'seed',now()),
  ('VCB','15m',1700086400000,94,94.2,93.8,94.1,25,'seed',now())
ON CONFLICT (ticker, tf, ts) DO UPDATE SET c = EXCLUDED.c, ingested_at = now();

INSERT INTO candles_latest (ticker, tf, ts, o, h, l, c, v, source, ingested_at)
VALUES
  ('VCB','1d',1700086400000,94,96,93,95,1200,'seed',now()),
  ('VCB','1h',1700086400000,94,95,93,94.5,100,'seed',now()),
  ('VCB','15m',1700086400000,94,94.2,93.8,94.1,25,'seed',now())
ON CONFLICT (ticker, tf) DO UPDATE SET ts = EXCLUDED.ts, c = EXCLUDED.c, ingested_at = now();

-- Corp actions
INSERT INTO corporate_actions (id,ticker,exchange,ex_date,record_date,pay_date,headline,event_type,source,source_url,raw_json,ingested_at)
VALUES ('seed-ca-1','VCB','HOSE','2026-02-20','2026-02-21','2026-02-28','Dividend cash 10%','dividend','seed','https://example.com/ca','{}'::jsonb,now())
ON CONFLICT (id) DO UPDATE SET ingested_at = now();

-- Financial surfaces
INSERT INTO fi_latest (ticker, period, statement, period_date, metric, value, fetched_at, ingested_at)
VALUES ('VCB','Q','is','2025-12-31','revenue',1234.5,now(),now())
ON CONFLICT (ticker, period, statement, period_date, metric) DO UPDATE SET value = EXCLUDED.value, ingested_at = now();

INSERT INTO financials (ticker, period, statement, period_date, metric, value, source, updated_at)
VALUES ('VCB','Q','is','2025-12-31','revenue',1234.5,'seed',now())
ON CONFLICT (ticker, period, statement, metric) DO UPDATE SET value = EXCLUDED.value, updated_at = now();

INSERT INTO fundamentals (ticker, metric, value, period, period_date, source, updated_at)
VALUES ('VCB','revenue',1234.5,'Q','2025-12-31','seed',now())
ON CONFLICT (ticker, metric) DO UPDATE SET value = EXCLUDED.value, updated_at = now();

INSERT INTO technical_indicators (ticker, tf, asof_ts, close, sma20, sma50, ema20, updated_at)
VALUES ('VCB','1d',1700086400000,95,93,90,94,now())
ON CONFLICT (ticker, tf) DO UPDATE SET close = EXCLUDED.close, updated_at = now();

INSERT INTO indicators (ticker, tf, indicator, value, asof_ts, updated_at)
VALUES ('VCB','1d','close',95,1700086400000,now())
ON CONFLICT (ticker, tf, indicator) DO UPDATE SET value = EXCLUDED.value, updated_at = now();

INSERT INTO market_stats (metric, value_numeric, value_text, asof_ts, updated_at)
VALUES
  ('candles_eligible_total', 1, NULL, 1700086400000, now()),
  ('candles_eligible_with_candles', 1, NULL, 1700086400000, now()),
  ('candles_eligible_missing', 0, NULL, 1700086400000, now()),
  ('candles_coverage_pct', 100, NULL, 1700086400000, now()),
  ('candles_frontier_status', NULL, 'fresh', 1700086400000, now()),
  ('candles_frontier_lag_ms', 1000, NULL, 1700086400000, now())
ON CONFLICT (metric) DO UPDATE SET value_numeric = EXCLUDED.value_numeric, value_text = EXCLUDED.value_text, updated_at = now();

INSERT INTO candle_repair_queue (ticker, tf, status, reason)
VALUES ('VCB', '1d', 'queued', 'seed')
ON CONFLICT DO NOTHING;

-- News for sentiment/context
INSERT INTO articles (url, title, source, published_at, text, fetch_status, fetched_at)
VALUES ('https://example.com/a1', 'VCB growth beats estimates', 'seed', now(), 'Strong profit and growth outlook', 'fetched', now())
ON CONFLICT (url) DO UPDATE SET fetch_status = 'fetched';

INSERT INTO article_symbols (article_url, ticker, method, confidence)
VALUES ('https://example.com/a1', 'VCB', 'seed', 0.9)
ON CONFLICT (article_url, ticker, method) DO UPDATE SET confidence = EXCLUDED.confidence;
