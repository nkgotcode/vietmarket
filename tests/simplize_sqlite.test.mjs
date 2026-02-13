import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { openDb, upsertRows, queryFi } from '../lib/simplize_sqlite.mjs';

test('sqlite upsert + query works', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'simplize-sqlite-'));
  const dbPath = path.join(dir, 'simplize.db');
  const db = openDb(dbPath);

  const rows = [
    { ticker: 'FPT', period: 'Q', statement: 'is', periodDate: '2025-12', periodDateName: 'Q4/2025', metric: 'is1', value: 10, fetchedAt: '2026-02-13T00:00:00Z' },
    { ticker: 'FPT', period: 'Q', statement: 'is', periodDate: '2025-12', periodDateName: 'Q4/2025', metric: 'is2', value: 20, fetchedAt: '2026-02-13T00:00:00Z' },
  ];

  upsertRows(db, rows);
  upsertRows(db, [{ ...rows[0], value: 11 }]);

  const got = queryFi(db, { ticker: 'FPT', period: 'Q', limit: 10 });
  assert.equal(got.length, 2);
  assert.ok(got.some((r) => r.metric === 'is1' && r.value === 11));
  db.close();
});
