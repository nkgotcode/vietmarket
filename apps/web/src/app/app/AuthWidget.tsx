import { UserButton } from '@clerk/nextjs';

/**
 * Auth widget.
 *
 * In Playwright E2E (E2E_BYPASS_AUTH=1) we bypass Clerk entirely.
 * We also suppress Clerk UI when the publishable key is not configured so local builds succeed.
 */
export default function AuthWidget() {
  if (process.env.E2E_BYPASS_AUTH === '1') return null;
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return null;
  return <UserButton />;
}
