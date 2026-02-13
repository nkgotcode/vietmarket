import test from 'node:test';
import assert from 'node:assert/strict';
import { stableStringify, blockHash, normalizeBlock } from '../lib/simplize_pipeline.mjs';

test('stableStringify is key-order independent', () => {
  const a = { z: 1, a: { b: 2, c: [3, { y: 9, x: 8 }] } };
  const b = { a: { c: [3, { x: 8, y: 9 }], b: 2 }, z: 1 };
  assert.equal(stableStringify(a), stableStringify(b));
  assert.equal(blockHash(a), blockHash(b));
});

test('normalizeBlock extracts statement numeric metrics only', () => {
  const block = {
    ticker: 'FPT',
    period: 'Q',
    fetchedAt: '2026-02-13T00:00:00.000Z',
    data: {
      is: { body: { data: { items: [{ periodDate: '2025-12', periodDateName: 'Q4/2025', is1: 10, is2: 20, foo: 'bar' }] } } },
      bs: { body: { data: { items: [{ periodDate: '2025-12', periodDateName: 'Q4/2025', bs1: 11 }] } } },
      cf: { body: { data: { items: [{ periodDate: '2025-12', periodDateName: 'Q4/2025', cf1: 12 }] } } },
      ratio: { body: { data: { items: [{ periodDate: '2025-12', periodDateName: 'Q4/2025', ratio1: 13, r2: 14 }] } } },
    },
  };

  const rows = normalizeBlock(block);
  assert.equal(rows.length, 6);
  assert.ok(rows.every((r) => r.ticker === 'FPT'));
  assert.ok(rows.some((r) => r.statement === 'is' && r.metric === 'is1' && r.value === 10));
  assert.ok(rows.some((r) => r.statement === 'ratio' && r.metric === 'ratio1' && r.value === 13));
  assert.ok(!rows.some((r) => r.metric === 'foo'));
});
