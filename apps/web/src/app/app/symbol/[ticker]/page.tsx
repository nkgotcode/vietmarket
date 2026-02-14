import Link from 'next/link';
import { UserButton } from '@clerk/nextjs';

export default async function SymbolPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <Link href="/app">← Back</Link>
          <h1 style={{ margin: '8px 0 0' }}>{ticker.toUpperCase()}</h1>
          <div style={{ color: '#666' }}>Charts + context will be wired from Convex next.</div>
        </div>
        <UserButton />
      </div>

      <ul style={{ marginTop: 16 }}>
        <li>
          <Link href="/app/chart-demo">Chart demo</Link>
        </li>
      </ul>
    </main>
  );
}
