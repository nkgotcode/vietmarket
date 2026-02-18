import Link from 'next/link';
import { UserButton } from '@clerk/nextjs';
import MarketOverviewClient from './MarketOverviewClient';
import HeadlinesClient from './HeadlinesClient';

export default function AppHome() {
  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>VietMarket</h1>
        <UserButton />
      </div>
      <p style={{ color: '#666' }}>
        Market overview (latest snapshot + top movers) is live below. Charts + Vietstock news coming next.
      </p>

      <ul>
        <li>
          <Link href="/app/chart-demo">Chart demo</Link>
        </li>
        <li>
          <Link href="/app/symbol/VCB">Symbol page</Link>
        </li>
      </ul>

      <MarketOverviewClient />
      <HeadlinesClient />
    </main>
  );
}
