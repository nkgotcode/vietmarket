export function resolveEffectivePeriod({ requestedPeriod, hasAuthToken, allowFallback = true }) {
  const p = String(requestedPeriod || 'Q').toUpperCase();
  if (p !== 'Y') return { requestedPeriod: p, effectivePeriod: p, fallbackApplied: false };
  if (hasAuthToken) return { requestedPeriod: 'Y', effectivePeriod: 'Y', fallbackApplied: false };
  if (allowFallback) {
    return {
      requestedPeriod: 'Y',
      effectivePeriod: 'Q',
      fallbackApplied: true,
      reason: 'missing_auth_token_for_yearly',
    };
  }
  return { requestedPeriod: 'Y', effectivePeriod: 'Y', fallbackApplied: false };
}
