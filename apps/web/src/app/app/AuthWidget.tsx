import { UserButton } from '@clerk/nextjs';

/**
 * Auth widget.
 *
 * In Playwright E2E (E2E_BYPASS_AUTH=1) we bypass Clerk entirely.
 */
export default function AuthWidget() {
  if (process.env.E2E_BYPASS_AUTH === '1') return null;
  return <UserButton />;
}
