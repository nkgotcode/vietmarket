-- VietMarket canonical TimescaleDB schema
-- Goals:
-- - Compatible with Convex candles (unix ms timestamps, same field names)
-- - Compatible with Vietstock archive metadata
-- - Efficient paging queries for chart scroll + common lookups

CREATE EXTENSION IF NOT EXISTS timescaledb;

-------------------------------------------------------------------------------
-- Candles (canonical full history)
-------------------------------------------------------------------------------

-- Note: we intentionally store ts as BIGINT unix milliseconds to match Convex.
CREATE TABLE IF NOT EXISTS candles (
  ticker      TEXT   NOT NULL,
  tf          TEXT   NOT NULL CHECK (tf IN ('1d','1h','15m')),
  ts          BIGINT NOT NULL, -- unix ms
  o           DOUBLE PRECISION NOT NULL,
  h           DOUBLE PRECISION NOT NULL,
  l           DOUBLE PRECISION NOT NULL,
  c           DOUBLE PRECISION NOT NULL,
  v           DOUBLE PRECISION NULL,
  source      TEXT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, tf, ts)
);

-- Create hypertable with ms time column.
-- 30-day chunks (in ms) is a reasonable starting point.
SELECT create_hypertable(
  'candles',
  'ts',
  chunk_time_interval => (1000::bigint) * 60 * 60 * 24 * 30,
  if_not_exists => TRUE
);

-- Core index for paging: newest-first for a symbol+tf
CREATE INDEX IF NOT EXISTS idx_candles_ticker_tf_ts_desc
  ON candles (ticker, tf, ts DESC);

-- Helpful for range scans by tf (optional analytics / backfills)
CREATE INDEX IF NOT EXISTS idx_candles_tf_ts_desc
  ON candles (tf, ts DESC);

-- Optional: BRIN can be very space-efficient for large append-mostly tables.
-- Keep it commented until needed.
-- CREATE INDEX IF NOT EXISTS brin_candles_ts ON candles USING brin (ts);

-------------------------------------------------------------------------------
-- Symbols (metadata)
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS symbols (
  ticker     TEXT PRIMARY KEY,
  name       TEXT NULL,
  exchange   TEXT NULL,
  active     BOOLEAN NULL,
  updated_at BIGINT NULL -- unix ms (Convex-compatible)
);

-- Lookup by exchange/active if you later need it
CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols (exchange);
CREATE INDEX IF NOT EXISTS idx_symbols_active ON symbols (active);

-------------------------------------------------------------------------------
-- Articles (Vietstock + future sources)
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS articles (
  url            TEXT PRIMARY KEY,
  canonical_url  TEXT NULL,
  source         TEXT NOT NULL,
  title          TEXT NOT NULL,
  published_at   TIMESTAMPTZ NULL,
  feed_url       TEXT NULL,

  discovered_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  fetched_at     TIMESTAMPTZ NULL,
  fetch_status   TEXT NOT NULL DEFAULT 'pending', -- pending|fetched|failed
  fetch_method   TEXT NULL,
  fetch_error    TEXT NULL,

  -- Full text (Option 2: no sqlite archive; store text directly)
  text           TEXT NULL,

  content_sha256 TEXT NULL,
  word_count     INTEGER NULL,
  lang           TEXT NULL,

  ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Backward-compatible migration if an older articles table exists
ALTER TABLE articles ADD COLUMN IF NOT EXISTS text TEXT;

-- Common query patterns:
-- - newest articles
-- - by published_at
-- - by fetch_status
-- - by feed_url
CREATE INDEX IF NOT EXISTS idx_articles_published_at_desc
  ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_discovered_at_desc
  ON articles (discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_fetch_status
  ON articles (fetch_status);
CREATE INDEX IF NOT EXISTS idx_articles_feed_url
  ON articles (feed_url);

-- Dedup helper if you ingest from multiple URLs pointing to same content
CREATE INDEX IF NOT EXISTS idx_articles_content_sha256
  ON articles (content_sha256);

-- Full text search (simple English; we can add Vietnamese config later)
CREATE INDEX IF NOT EXISTS idx_articles_text_fts
  ON articles USING GIN (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(text,'')));

-------------------------------------------------------------------------------
-- Article ↔ Symbol links
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS article_symbols (
  article_url TEXT NOT NULL REFERENCES articles(url) ON DELETE CASCADE,
  ticker      TEXT NOT NULL REFERENCES symbols(ticker) ON DELETE CASCADE,
  confidence  DOUBLE PRECISION NULL,
  method      TEXT NULL,
  PRIMARY KEY (article_url, ticker)
);

-------------------------------------------------------------------------------
-- RSS ingestion state (Option 2: no sqlite)
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS feeds (
  feed_url TEXT PRIMARY KEY,
  kind     TEXT NOT NULL DEFAULT 'rss',
  title    TEXT NULL,
  last_seen_published_at TIMESTAMPTZ NULL,
  last_checked_at TIMESTAMPTZ NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seeds (
  seed_url   TEXT PRIMARY KEY,
  feed_url   TEXT NULL REFERENCES feeds(feed_url) ON DELETE SET NULL,
  channel_id INTEGER NULL,
  kind       TEXT NOT NULL DEFAULT 'category',
  note       TEXT NULL,
  enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawl_state (
  seed_url  TEXT PRIMARY KEY REFERENCES seeds(seed_url) ON DELETE CASCADE,
  next_page INTEGER NOT NULL DEFAULT 1,
  done      BOOLEAN NOT NULL DEFAULT FALSE,
  no_new_pages BOOLEAN NOT NULL DEFAULT FALSE,
  last_crawled_at TIMESTAMPTZ NULL,
  oldest_seen_published_at TIMESTAMPTZ NULL,
  last_error TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_seeds_feed_url ON seeds(feed_url);
CREATE INDEX IF NOT EXISTS idx_seeds_enabled ON seeds(enabled);
CREATE INDEX IF NOT EXISTS idx_crawl_state_done ON crawl_state(done);

CREATE INDEX IF NOT EXISTS idx_article_symbols_ticker
  ON article_symbols (ticker);

CREATE INDEX IF NOT EXISTS idx_article_symbols_article
  ON article_symbols (article_url);

-------------------------------------------------------------------------------
-- Fundamentals / facts (Simplize)
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fi_latest (
  ticker       TEXT NOT NULL REFERENCES symbols(ticker) ON DELETE CASCADE,
  period       TEXT NOT NULL,
  statement    TEXT NOT NULL,
  period_date  DATE NULL,
  metric       TEXT NOT NULL,
  value        DOUBLE PRECISION NULL,
  fetched_at   TIMESTAMPTZ NULL,
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period, statement, metric)
);

-- Most common lookups:
-- - latest by ticker
-- - metric time series / screening by metric
CREATE INDEX IF NOT EXISTS idx_fi_latest_ticker
  ON fi_latest (ticker);

CREATE INDEX IF NOT EXISTS idx_fi_latest_ticker_metric
  ON fi_latest (ticker, metric);

CREATE INDEX IF NOT EXISTS idx_fi_latest_metric
  ON fi_latest (metric);
