import Link from 'next/link';
import { UserButton } from '@clerk/nextjs';

export default function AppHome() {
  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>VietMarket</h1>
        <UserButton />
      </div>
      <p style={{ color: '#666' }}>
        First version will include charts (KLineChart) + Vietstock news + ticker context.
      </p>

      <ul>
        <li>
          <Link href="/app/chart-demo">Chart demo</Link>
        </li>
      </ul>
    </main>
  );
}
