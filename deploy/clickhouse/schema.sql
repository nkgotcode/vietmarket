CREATE DATABASE IF NOT EXISTS vietmarket;

CREATE TABLE IF NOT EXISTS vietmarket.candles (
  ticker LowCardinality(String),
  tf     LowCardinality(String),
  ts     DateTime64(3, 'UTC'),
  o      Float64,
  h      Float64,
  l      Float64,
  c      Float64,
  v      Nullable(Float64),
  source LowCardinality(Nullable(String)),
  ingested_at DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY tf
ORDER BY (ticker, tf, ts);

-- Helpful for "scroll back" paging
-- Query pattern:
-- SELECT ... FROM candles WHERE ticker=? AND tf=? AND ts < ? ORDER BY ts DESC LIMIT ?
