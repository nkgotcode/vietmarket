-- Local SQLite schema for Vietstock Archive

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feeds (
  feed_url TEXT PRIMARY KEY,
  kind TEXT NOT NULL, -- 'rss'
  title TEXT,
  last_seen_published_at TEXT,
  last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS seeds (
  seed_url TEXT PRIMARY KEY,
  feed_url TEXT,
  channel_id INTEGER, -- derived from RSS numeric id
  kind TEXT NOT NULL, -- 'category'
  note TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS crawl_state (
  seed_url TEXT PRIMARY KEY,
  next_page INTEGER NOT NULL DEFAULT 1,
  done INTEGER NOT NULL DEFAULT 0,
  no_new_pages INTEGER NOT NULL DEFAULT 0,
  last_crawled_at TEXT,
  oldest_seen_published_at TEXT,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS articles (
  url TEXT PRIMARY KEY,
  canonical_url TEXT,
  title TEXT,
  published_at TEXT,
  source TEXT, -- 'rss' | 'backfill'
  feed_url TEXT,
  discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
  fetched_at TEXT,
  fetch_status TEXT NOT NULL DEFAULT 'pending', -- pending|fetched|failed
  fetch_method TEXT, -- http|playwright
  fetch_error TEXT,
  html_path TEXT,
  text_path TEXT,
  content_sha256 TEXT,
  word_count INTEGER,
  lang TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(fetch_status);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_discovered ON articles(discovered_at);

-- Optional analysis tables (not required for initial ingestion)
CREATE TABLE IF NOT EXISTS analysis (
  url TEXT PRIMARY KEY REFERENCES articles(url) ON DELETE CASCADE,
  sentiment REAL,
  summary TEXT,
  analyzed_at TEXT,
  model TEXT
);
