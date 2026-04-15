import Link from 'next/link';
import MarketOverviewClient from './MarketOverviewClient';
import HeadlinesClient from './HeadlinesClient';
import AuthWidget from './AuthWidget';

export default function AppHome() {
  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>VietMarket</h1>
        <AuthWidget />
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
        <li>
          <Link href="/app/health">Control plane health</Link>
        </li>
        <li>
          <Link href="/app/regime">Market regime</Link>
        </li>
        <li>
          <Link href="/app/watchlist">Supervisor watchlist</Link>
        </li>
        <li>
          <Link href="/app/signals">Signal engine</Link>
        </li>
        <li>
          <Link href="/app/recommendations">Recommendations</Link>
        </li>
        <li>
          <Link href="/app/briefing">Briefing</Link>
        </li>
        <li>
          <Link href="/app/portfolio">Portfolio</Link>
        </li>
        <li>
          <Link href="/app/orders">Orders</Link>
        </li>
        <li>
          <Link href="/app/journal">Journal</Link>
        </li>
        <li>
          <Link href="/app/alerts">Alerts</Link>
        </li>
        <li>
          <Link href="/app/system">System</Link>
        </li>
        <li>
          <Link href="/app/evaluation">Evaluation</Link>
        </li>
        <li>
          <Link href="/app/delivery">Delivery</Link>
        </li>
        <li>
          <Link href="/app/operator-control">Operator control</Link>
        </li>
        <li>
          <Link href="/app/execution">Execution</Link>
        </li>
        <li>
          <Link href="/app/ticker-state/VCB">Ticker state</Link>
        </li>
      </ul>

      <MarketOverviewClient />
      <HeadlinesClient />
    </main>
  );
}
