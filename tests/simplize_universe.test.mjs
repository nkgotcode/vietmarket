import test from 'node:test';
import assert from 'node:assert/strict';
import { chunk } from '../lib/simplize_universe.mjs';

test('chunk splits arrays correctly', () => {
  const a = [1,2,3,4,5];
  const c = chunk(a, 2);
  assert.equal(c.length, 3);
  assert.deepEqual(c[0], [1,2]);
  assert.deepEqual(c[2], [5]);
});
