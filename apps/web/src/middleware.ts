import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Public routes: landing + Clerk auth pages.
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
]);

export default clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) return;
  await auth.protect();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files.
    '/((?!_next|.*\\..*).*)',
  ],
};
