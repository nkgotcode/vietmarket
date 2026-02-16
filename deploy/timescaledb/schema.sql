-- TimescaleDB schema for VietMarket candles
-- Assumes DB=vietmarket, user=vietmarket

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS candles (
  ticker      TEXT        NOT NULL,
  tf          TEXT        NOT NULL,
  ts          TIMESTAMPTZ NOT NULL,
  o           DOUBLE PRECISION,
  h           DOUBLE PRECISION,
  l           DOUBLE PRECISION,
  c           DOUBLE PRECISION,
  v           DOUBLE PRECISION,
  source      TEXT,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, tf, ts)
);

-- Convert to hypertable (idempotent)
SELECT create_hypertable('candles', 'ts', if_not_exists => TRUE);

-- Paging index for "give me N candles before ts" queries
CREATE INDEX IF NOT EXISTS candles_ticker_tf_ts_desc
  ON candles (ticker, tf, ts DESC);

-- Optional: helpful if you later do TF-wide scans
CREATE INDEX IF NOT EXISTS candles_tf_ts_desc
  ON candles (tf, ts DESC);
