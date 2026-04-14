import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Public routes: landing + Clerk auth pages.
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
]);

export default clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) return;

  // Playwright E2E bypass (test-only). Requires env + header.
  if (process.env.E2E_BYPASS_AUTH === '1') {
    const tok = process.env.E2E_BYPASS_TOKEN;
    if (tok && req.headers.get('x-e2e-bypass') === tok) {
      return;
    }
  }

  await auth.protect();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files.
    '/((?!_next|.*\\..*).*)',
  ],
};
