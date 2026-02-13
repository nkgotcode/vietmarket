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

export function querySymbols(db, { limit = 200, q = '' } = {}) {
  if (q) {
    return db.prepare(`
      SELECT ticker, name, exchange, firstSeenAt, lastSeenAt
      FROM symbols
      WHERE ticker LIKE ? OR COALESCE(name,'') LIKE ?
      ORDER BY lastSeenAt DESC
      LIMIT ?
    `).all(`%${q.toUpperCase()}%`, `%${q}%`, limit);
  }
  return db.prepare(`
    SELECT ticker, name, exchange, firstSeenAt, lastSeenAt
    FROM symbols
    ORDER BY lastSeenAt DESC
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
