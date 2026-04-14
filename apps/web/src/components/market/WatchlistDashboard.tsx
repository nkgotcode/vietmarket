'use client';

import { useEffect, useState } from 'react';

import WatchlistTable from '@/components/market/WatchlistTable';

type CycleRow = Record<string, unknown> | null;

type WatchlistRow = {
  ticker: string;
  sector: string | null;
  industry_name: string | null;
  icb_code: string | null;
  industry_code: string | null;
  price_last: number | null;
  ret_1d: number | null;
  ret_5d: number | null;
  watchlist_score: number;
  trend_state: string;
  momentum_state: string;
  liquidity_bucket: string;
  article_count_24h: number;
  classification_source?: string | null;
};

type Payload = {
  ok: boolean;
  cycle: CycleRow;
  rows: WatchlistRow[];
};

export default function WatchlistDashboard() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await fetch('/api/brain/watchlist', { cache: 'no-store' }).then((r) => r.json() as Promise<Payload>);
        if (cancelled) return;
        setPayload(result);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load watchlist');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!payload) return <p>Loading watchlist…</p>;

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ color: '#666' }}>
        Latest cycle-backed watchlist ordered by deterministic Phase 2 market-state score, with explicit canonical classification codes.
      </div>
      <WatchlistTable rows={payload.rows} />
    </section>
  );
}
