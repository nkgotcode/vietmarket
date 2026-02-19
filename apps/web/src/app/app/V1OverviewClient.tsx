'use client';

import { useEffect, useState } from 'react';
import { fetchAnalyticsOverview, fetchOverallHealth, fetchSentimentOverview } from '@/lib/historyApi';

function badge(frontier: any) {
  const lag = Number(frontier?.lag_ms ?? 0);
  const status = String(frontier?.status || '').toLowerCase();
  if (status === 'fresh' && lag <= 2 * 60 * 60 * 1000) return { text: 'Fresh', bg: '#e8f5e9', fg: '#1b5e20' };
  return { text: 'Degraded', bg: '#fff3e0', fg: '#e65100' };
}

export default function V1OverviewClient() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [a, h, s] = await Promise.all([
          fetchAnalyticsOverview(),
          fetchOverallHealth(),
          fetchSentimentOverview({ windowDays: 7, limit: 5 }),
        ]);
        setData({ a, h, s });
      } catch (e: any) {
        setErr(e?.message || String(e));
      }
    })();
  }, []);

  if (err) return <p style={{ color: '#b00020' }}>{err}</p>;
  if (!data) return <p style={{ color: '#666' }}>Loading v1 analytics…</p>;

  const b = badge(data.h?.frontier);
  return (
    <section style={{ marginTop: 20, border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <h2 style={{ marginTop: 0 }}>v1 analytics + health</h2>
      <div style={{ display: 'inline-block', padding: '4px 10px', borderRadius: 999, background: b.bg, color: b.fg, fontWeight: 600 }}>
        {b.text}
      </div>
      <ul style={{ marginTop: 10, color: '#333' }}>
        <li>Candles rows: {data.a?.candles_rows ?? '—'}</li>
        <li>Coverage: {data.a?.coverage_pct != null ? `${Number(data.a.coverage_pct).toFixed(2)}%` : '—'}</li>
        <li>Repair queue queued: {data.h?.repair_queue?.queued ?? '—'}</li>
        <li>Sentiment articles (7d): {data.s?.overall?.articles ?? '—'}</li>
      </ul>
    </section>
  );
}
