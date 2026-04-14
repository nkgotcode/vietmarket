import Link from 'next/link';

import TickerStateDashboard from '@/components/market/TickerStateDashboard';

export default async function TickerStatePage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();

  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'grid', gap: 8 }}>
        <Link href="/app/watchlist">← Back to watchlist</Link>
        <h1 style={{ margin: 0 }}>Ticker state: {symbol}</h1>
        <p style={{ color: '#666', marginTop: 0 }}>
          Deterministic Phase 2 ticker snapshot built from Timescale/Postgres market-state tables, including canonical sector, industry, and ICB classification codes.
        </p>
      </div>
      <TickerStateDashboard ticker={symbol} />
    </main>
  );
}
