import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { openRegistryDb, upsertSymbol, upsertArticle, upsertArticleSymbol, queryContext } from '../lib/registry_sqlite.mjs';

test('registry basic upsert and context query', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'registry-'));
  const db = openRegistryDb(path.join(dir, 'r.db'));
  const now = new Date().toISOString();

  upsertSymbol(db, { ticker: 'FPT', name: 'FPT Corp', seenAt: now });
  upsertArticle(db, { url: 'https://example.com/a', title: 'FPT tăng trưởng', source: 'vietstock', ingestedAt: now, publishedAt: now });
  upsertArticleSymbol(db, { url: 'https://example.com/a', ticker: 'FPT', confidence: 0.7, method: 'title_regex' });

  const ctx = queryContext(db, { ticker: 'FPT', limitArticles: 5 });
  assert.equal(ctx.symbol.ticker, 'FPT');
  assert.equal(ctx.articles.length, 1);
  db.close();
});
