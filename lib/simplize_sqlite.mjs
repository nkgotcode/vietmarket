import { DatabaseSync } from 'node:sqlite';

export function openDb(dbPath) {
  const db = new DatabaseSync(dbPath);
  db.exec(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS fi_points (
      ticker TEXT NOT NULL,
      period TEXT NOT NULL,
      statement TEXT NOT NULL,
      periodDate TEXT,
      periodDateName TEXT,
      metric TEXT NOT NULL,
      value REAL NOT NULL,
      fetchedAt TEXT NOT NULL,
      PRIMARY KEY (ticker, period, statement, periodDate, metric)
    );
    CREATE INDEX IF NOT EXISTS idx_fi_lookup ON fi_points(ticker, period, statement, periodDate);
  `);
  return db;
}

export function upsertRows(db, rows) {
  const stmt = db.prepare(`
    INSERT INTO fi_points (ticker, period, statement, periodDate, periodDateName, metric, value, fetchedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, period, statement, periodDate, metric)
    DO UPDATE SET value=excluded.value, periodDateName=excluded.periodDateName, fetchedAt=excluded.fetchedAt
  `);

  db.exec('BEGIN');
  try {
    for (const r of rows) {
      stmt.run(
        r.ticker,
        r.period,
        r.statement,
        r.periodDate,
        r.periodDateName,
        r.metric,
        r.value,
        r.fetchedAt,
      );
    }
    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch {}
    throw err;
  }
}

export function queryFi(db, { ticker, period = 'Q', statement = null, limit = 500 }) {
  const base = `SELECT ticker, period, statement, periodDate, periodDateName, metric, value, fetchedAt
                FROM fi_points
                WHERE ticker = ? AND period = ?`;
  if (statement) {
    return db.prepare(`${base} AND statement = ? ORDER BY periodDate DESC, metric ASC LIMIT ?`).all(ticker, period, statement, limit);
  }
  return db.prepare(`${base} ORDER BY periodDate DESC, statement ASC, metric ASC LIMIT ?`).all(ticker, period, limit);
}
