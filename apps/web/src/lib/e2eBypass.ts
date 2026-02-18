import 'server-only';

/**
 * E2E auth bypass.
 *
 * This is ONLY for Playwright runs. Do not enable in production.
 *
 * Enable by setting:
 * - E2E_BYPASS_AUTH=1
 * - E2E_BYPASS_TOKEN=<some random string>
 *
 * Then send header:
 * - x-e2e-bypass: <token>
 */
export function isE2EBypass(req: Request): boolean {
  if (process.env.E2E_BYPASS_AUTH !== '1') return false;
  const tok = process.env.E2E_BYPASS_TOKEN;
  if (!tok) return false;
  const got = req.headers.get('x-e2e-bypass');
  return got === tok;
}
