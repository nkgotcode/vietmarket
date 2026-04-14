'use client';

import { useEffect, useState } from 'react';

import RegimeCard from '@/components/market/RegimeCard';
import TickerSnapshotCard from '@/components/market/TickerSnapshotCard';

type CycleRow = Record<string, unknown> | null;

type SnapshotRow = {
  ticker: string;
  exchange: string | null;
  sector: string | null;
  industry_name: string | null;
  icb_code: string | null;
  industry_code: string | null;
  classification_source?: string | null;
  price_last: number | null;
  volume_last: number | null;
  turnover_last: number | null;
  ret_1d: number | null;
  ret_5d: number | null;
  ret_20d: number | null;
  sma20_gap: number | null;
  sma50_gap: number | null;
  ema20_gap: number | null;
  volatility_20d: number | null;
  article_count_24h: number;
  corporate_action_flag: boolean;
  financial_recency_days: number | null;
  liquidity_bucket: string;
  trend_state: string;
  momentum_state: string;
  watchlist_score: number;
  health_status: string;
  snapshot_json?: Record<string, unknown> | null;
};

type RegimeRow = {
  market_regime: string;
  breadth_state: string;
  trend_state: string;
  liquidity_state: string;
  event_pressure_state: string;
  confidence: number;
  watchlist_count: number;
  reasoning_json?: Record<string, unknown> | null;
} | null;

type SectorRow = {
  sector: string;
  names_count: number;
  breadth_pct: number | null;
  avg_ret_5d: number | null;
} | null;

type Payload = {
  ok: boolean;
  cycle: CycleRow;
  snapshot: SnapshotRow;
  regime: RegimeRow;
  sector: SectorRow;
  error?: string;
};

export default function TickerStateDashboard({ ticker }: { ticker: string }) {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`/api/brain/ticker/${ticker}`, { cache: 'no-store' });
        const result = (await response.json()) as Payload;
        if (!response.ok) {
          throw new Error(result.error || 'Failed to load ticker state');
        }
        if (cancelled) return;
        setPayload(result);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load ticker state');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!payload) return <p>Loading ticker state…</p>;

  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <TickerSnapshotCard snapshot={payload.snapshot} />
      <div>
        <h3 style={{ marginBottom: 8 }}>Current regime context</h3>
        <RegimeCard regime={payload.regime} />
      </div>
      {payload.sector ? (
        <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Sector context</h3>
          <div><strong>{payload.sector.sector}</strong></div>
          <div style={{ color: '#666' }}>
            Names: {payload.sector.names_count} • Breadth: {payload.sector.breadth_pct ?? '—'} • Avg 5D: {payload.sector.avg_ret_5d ?? '—'}
          </div>
          <div style={{ color: '#888', fontSize: 12, marginTop: 8 }}>
            Classification: {payload.snapshot.industry_name ?? '—'} • ICB {payload.snapshot.icb_code ?? '—'} • Industry {payload.snapshot.industry_code ?? '—'}
          </div>
        </div>
      ) : null}
    </section>
  );
}
