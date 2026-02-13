import { DatabaseSync } from 'node:sqlite';

export function openRegistryDb(dbPath) {
  const db = new DatabaseSync(dbPath);
  db.exec(`
    PRAGMA journal_mode = WAL;

    CREATE TABLE IF NOT EXISTS symbols (
      ticker TEXT PRIMARY KEY,
      name TEXT,
      exchange TEXT,
      active INTEGER NOT NULL DEFAULT 1,
      firstSeenAt TEXT NOT NULL,
      lastSeenAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS symbol_source (
      ticker TEXT NOT NULL,
      source TEXT NOT NULL,
      sourceRef TEXT,
      firstSeenAt TEXT NOT NULL,
      lastSeenAt TEXT NOT NULL,
      PRIMARY KEY (ticker, source, sourceRef)
    );

    CREATE TABLE IF NOT EXISTS articles (
      url TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      publishedAt TEXT,
      wordCount INTEGER,
      source TEXT NOT NULL,
      ingestedAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS article_symbols (
      url TEXT NOT NULL,
      ticker TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 0.5,
      method TEXT NOT NULL,
      PRIMARY KEY (url, ticker, method)
    );

    CREATE INDEX IF NOT EXISTS idx_symbols_lastSeen ON symbols(lastSeenAt DESC);
    CREATE INDEX IF NOT EXISTS idx_source_ticker ON symbol_source(ticker, source);
    CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(publishedAt DESC);
    CREATE INDEX IF NOT EXISTS idx_article_symbols_ticker ON article_symbols(ticker, url);
    CREATE INDEX IF NOT EXISTS idx_article_symbols_url ON article_symbols(url);

    CREATE TABLE IF NOT EXISTS fi_latest (
      ticker TEXT NOT NULL,
      period TEXT NOT NULL,
      statement TEXT NOT NULL,
      periodDate TEXT,
      metric TEXT NOT NULL,
      value REAL,
      fetchedAt TEXT,
      PRIMARY KEY (ticker, period, statement, periodDate, metric)
    );

    CREATE INDEX IF NOT EXISTS idx_fi_latest_lookup ON fi_latest(ticker, period, statement, periodDate DESC);

    CREATE TABLE IF NOT EXISTS symbol_context_latest (
      ticker TEXT PRIMARY KEY,
      latestNewsAt TEXT,
      articleCount30d INTEGER NOT NULL DEFAULT 0,
      latestFiAt TEXT,
      fiMetricCount INTEGER NOT NULL DEFAULT 0,
      updatedAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS registry_kv (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updatedAt TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  return db;
}

export function upsertSymbol(db, { ticker, name = null, exchange = null, seenAt }) {
  db.prepare(`
    INSERT INTO symbols (ticker, name, exchange, firstSeenAt, lastSeenAt)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(ticker) DO UPDATE SET
      name = COALESCE(excluded.name, symbols.name),
      exchange = COALESCE(excluded.exchange, symbols.exchange),
      lastSeenAt = excluded.lastSeenAt,
      active = 1
  `).run(ticker, name, exchange, seenAt, seenAt);
}

export function upsertSymbolSource(db, { ticker, source, sourceRef = null, seenAt }) {
  db.prepare(`
    INSERT INTO symbol_source (ticker, source, sourceRef, firstSeenAt, lastSeenAt)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(ticker, source, sourceRef) DO UPDATE SET
      lastSeenAt = excluded.lastSeenAt
  `).run(ticker, source, sourceRef, seenAt, seenAt);
}

export function upsertArticle(db, { url, title, publishedAt = null, wordCount = null, source, ingestedAt }) {
  db.prepare(`
    INSERT INTO articles (url, title, publishedAt, wordCount, source, ingestedAt)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(url) DO UPDATE SET
      title = excluded.title,
      publishedAt = COALESCE(excluded.publishedAt, articles.publishedAt),
      wordCount = COALESCE(excluded.wordCount, articles.wordCount),
      ingestedAt = excluded.ingestedAt
  `).run(url, title, publishedAt, wordCount, source, ingestedAt);
}

export function upsertArticleSymbol(db, { url, ticker, confidence = 0.5, method = 'title_regex' }) {
  db.prepare(`
    INSERT INTO article_symbols (url, ticker, confidence, method)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(url, ticker, method) DO UPDATE SET
      confidence = MAX(article_symbols.confidence, excluded.confidence)
  `).run(url, ticker, confidence, method);
}

export function replaceFiLatest(db, rows) {
  db.exec('DELETE FROM fi_latest');
  if (!rows?.length) return;
  const stmt = db.prepare(`
    INSERT INTO fi_latest (ticker, period, statement, periodDate, metric, value, fetchedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  db.exec('BEGIN');
  try {
    for (const r of rows) {
      stmt.run(r.ticker, r.period, r.statement, r.periodDate, r.metric, r.value, r.fetchedAt);
    }
    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch {}
    throw err;
  }
}

export function rebuildContextLatest(db, nowIso) {
  db.exec('DELETE FROM symbol_context_latest');
  const stmt = db.prepare(`
    INSERT INTO symbol_context_latest (ticker, latestNewsAt, articleCount30d, latestFiAt, fiMetricCount, updatedAt)
    SELECT
      s.ticker,
      (
        SELECT MAX(a.publishedAt)
        FROM article_symbols x
        JOIN articles a ON a.url = x.url
        WHERE x.ticker = s.ticker
      ) AS latestNewsAt,
      (
        SELECT COUNT(*)
        FROM article_symbols x
        JOIN articles a ON a.url = x.url
        WHERE x.ticker = s.ticker
          AND a.publishedAt >= datetime('now', '-30 day')
      ) AS articleCount30d,
      (
        SELECT MAX(f.fetchedAt)
        FROM fi_latest f
        WHERE f.ticker = s.ticker
      ) AS latestFiAt,
      (
        SELECT COUNT(*)
        FROM fi_latest f
        WHERE f.ticker = s.ticker
      ) AS fiMetricCount,
      ? AS updatedAt
    FROM symbols s
  `);
  stmt.run(nowIso);
}

export function querySymbols(db, { limit = 200, q = '' } = {}) {
  if (q) {
    return db.prepare(`
      SELECT s.ticker, s.name, s.exchange, s.firstSeenAt, s.lastSeenAt,
             c.latestNewsAt, c.articleCount30d, c.latestFiAt, c.fiMetricCount
      FROM symbols s
      LEFT JOIN symbol_context_latest c ON c.ticker = s.ticker
      WHERE s.ticker LIKE ? OR COALESCE(s.name,'') LIKE ?
      ORDER BY s.lastSeenAt DESC
      LIMIT ?
    `).all(`%${q.toUpperCase()}%`, `%${q}%`, limit);
  }
  return db.prepare(`
    SELECT s.ticker, s.name, s.exchange, s.firstSeenAt, s.lastSeenAt,
           c.latestNewsAt, c.articleCount30d, c.latestFiAt, c.fiMetricCount
    FROM symbols s
    LEFT JOIN symbol_context_latest c ON c.ticker = s.ticker
    ORDER BY s.lastSeenAt DESC
    LIMIT ?
  `).all(limit);
}

export function queryContext(db, { ticker, limitArticles = 10 }) {
  const symbol = db.prepare(`SELECT * FROM symbols WHERE ticker = ?`).get(ticker) || null;
  const articles = db.prepare(`
    SELECT a.url, a.title, a.publishedAt, a.wordCount, s.confidence, s.method
    FROM article_symbols s
    JOIN articles a ON a.url = s.url
    WHERE s.ticker = ?
    ORDER BY a.publishedAt DESC
    LIMIT ?
  `).all(ticker, limitArticles);
  return { symbol, articles };
}
