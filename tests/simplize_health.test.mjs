import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateFreshness } from '../lib/simplize_health.mjs';

test('evaluateFreshness handles missing timestamp', () => {
  const r = evaluateFreshness(Date.now(), null, 1000);
  assert.equal(r.ok, false);
  assert.equal(r.reason, 'missing_timestamp');
});

test('evaluateFreshness marks stale', () => {
  const now = 20000;
  const last = 1000;
  const r = evaluateFreshness(now, last, 5000);
  assert.equal(r.ok, false);
  assert.equal(r.reason, 'stale');
});

test('evaluateFreshness marks fresh', () => {
  const now = 20000;
  const last = 18000;
  const r = evaluateFreshness(now, last, 5000);
  assert.equal(r.ok, true);
  assert.equal(r.reason, 'fresh');
});
