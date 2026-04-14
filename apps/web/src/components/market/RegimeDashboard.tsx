'use client';

import { useEffect, useState } from 'react';

import RegimeCard from '@/components/market/RegimeCard';
import SectorTable from '@/components/market/SectorTable';

type CycleRow = Record<string, unknown> | null;

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
  adv_count: number;
  dec_count: number;
  breadth_pct: number | null;
  avg_ret_1d: number | null;
  avg_ret_5d: number | null;
};

type Payload = {
  ok: boolean;
  cycle: CycleRow;
  regime: RegimeRow;
};

type SectorPayload = {
  ok: boolean;
  rows: SectorRow[];
};

export default function RegimeDashboard() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [sectors, setSectors] = useState<SectorPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [regime, sectorRows] = await Promise.all([
          fetch('/api/brain/regime', { cache: 'no-store' }).then((r) => r.json() as Promise<Payload>),
          fetch('/api/brain/sectors', { cache: 'no-store' }).then((r) => r.json() as Promise<SectorPayload>),
        ]);
        if (cancelled) return;
        setPayload(regime);
        setSectors(sectorRows);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load regime state');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!payload || !sectors) return <p>Loading market regime…</p>;

  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <RegimeCard regime={payload.regime} />
      <div>
        <h3 style={{ marginBottom: 8 }}>Sector breadth</h3>
        <SectorTable rows={sectors.rows} />
      </div>
    </section>
  );
}
