import { UserButton } from '@clerk/nextjs';

export default function AppHome() {
  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>App</h1>
        <UserButton />
      </div>
      <p style={{ color: '#666' }}>
        Next: wire Convex queries (days, articles, symbols, FI) and the 15-minute sync worker.
      </p>
    </main>
  );
}
