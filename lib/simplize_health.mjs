export function evaluateFreshness(nowMs, lastUpdatedMs, maxAgeMs) {
  if (!Number.isFinite(lastUpdatedMs) || lastUpdatedMs <= 0) {
    return { ok: false, ageMs: null, reason: 'missing_timestamp' };
  }
  const ageMs = nowMs - lastUpdatedMs;
  if (ageMs < 0) {
    return { ok: true, ageMs, reason: 'clock_skew' };
  }
  if (ageMs > maxAgeMs) {
    return { ok: false, ageMs, reason: 'stale' };
  }
  return { ok: true, ageMs, reason: 'fresh' };
}
