'use client';

import { useEffect, useState } from 'react';
import PortfolioSummary from '@/components/portfolio/PortfolioSummary';
import PnLChart from '@/components/portfolio/PnLChart';

type PortfolioPayload = {
  ok: boolean;
  snapshot: {
    cycle_id: string;
    cash_balance: number;
    market_value: number;
    unrealized_pnl: number;
    realized_pnl: number;
    positions_count: number;
    created_at: string;
  } | null;
  positions: Array<{
    ticker: string;
    qty: number;
    avg_cost: number;
    market_price: number | null;
    market_value: number | null;
    unrealized_pnl: number;
    realized_pnl: number;
    updated_at: string;
  }>;
};

export default function PortfolioPage() {
  const [data, setData] = useState<PortfolioPayload | null>(null);
  useEffect(() => { fetch('/api/brain/portfolio', { cache: 'no-store' }).then((r) => r.json() as Promise<PortfolioPayload>).then(setData); }, []);
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Portfolio</h1>
      {!data ? <p>Loading portfolio…</p> : <><PortfolioSummary snapshot={data.snapshot} positions={data.positions} /><h3>PnL history</h3><PnLChart rows={(data.snapshot ? [data.snapshot] : [])} /></>}
    </main>
  );
}
