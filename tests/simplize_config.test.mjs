import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveEffectivePeriod } from '../lib/simplize_config.mjs';

test('resolveEffectivePeriod keeps Y when token exists', () => {
  const r = resolveEffectivePeriod({ requestedPeriod: 'Y', hasAuthToken: true, allowFallback: true });
  assert.equal(r.effectivePeriod, 'Y');
  assert.equal(r.fallbackApplied, false);
});

test('resolveEffectivePeriod falls back Y->Q when no token and fallback enabled', () => {
  const r = resolveEffectivePeriod({ requestedPeriod: 'Y', hasAuthToken: false, allowFallback: true });
  assert.equal(r.effectivePeriod, 'Q');
  assert.equal(r.fallbackApplied, true);
});
