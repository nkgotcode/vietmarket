import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { openRegistryDb } from '../lib/registry_sqlite.mjs';

test('registry_kv exists and supports upsert', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'registry-'));
  const db = openRegistryDb(path.join(dir, 'r.db'));
  db.prepare("INSERT INTO registry_kv(key,value) VALUES('a','1')").run();
  db.prepare("INSERT INTO registry_kv(key,value) VALUES('a','2') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
  const row = db.prepare("SELECT value FROM registry_kv WHERE key='a'").get();
  assert.equal(row.value, '2');
  db.close();
});
