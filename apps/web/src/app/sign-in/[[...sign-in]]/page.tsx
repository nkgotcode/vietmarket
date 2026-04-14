import { SignIn } from '@clerk/nextjs';

export default function Page() {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  return (
    <main style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 24 }}>
      {publishableKey ? (
        <SignIn />
      ) : (
        <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, maxWidth: 520 }}>
          Clerk sign-in is disabled because NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is not configured in this environment.
        </div>
      )}
    </main>
  );
}
