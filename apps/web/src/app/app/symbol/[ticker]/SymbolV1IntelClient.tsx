'use client';

import { useEffect, useState } from 'react';
import { fetchTickerContext, fetchTickerSentiment, fetchOverallHealth } from '@/lib/historyApi';

export default function SymbolV1IntelClient({ ticker }: { ticker: string }) {
  const [ctx, setCtx] = useState<any>(null);
  const [sent, setSent] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [c, s, h] = await Promise.all([
          fetchTickerContext(ticker),
          fetchTickerSentiment(ticker, { windowDays: 30 }),
          fetchOverallHealth(),
        ]);
        setCtx(c);
        setSent(s);
        setHealth(h);
      } catch (e: any) {
        setErr(e?.message || String(e));
      }
    })();
  }, [ticker]);

  if (err) return <p style={{ color: '#b00020' }}>{err}</p>;
  if (!ctx || !sent || !health) return <p style={{ color: '#666' }}>Loading context + sentiment…</p>;

  const lagMs = Number(health?.frontier?.lag_ms ?? 0);
  const isDegraded = String(health?.frontier?.status || '').toLowerCase() !== 'fresh' || lagMs > 2 * 60 * 60 * 1000;

  return (
    <section style={{ marginTop: 16, border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <h3 style={{ marginTop: 0 }}>Ticker intelligence (v1)</h3>
      <p>
        <strong>Status:</strong>{' '}
        <span style={{ color: isDegraded ? '#e65100' : '#1b5e20', fontWeight: 600 }}>{isDegraded ? 'Degraded' : 'Fresh'}</span>
      </p>
      <p><strong>Sentiment score:</strong> {sent?.summary?.avg_score ?? '—'} from {sent?.summary?.articles ?? 0} articles</p>
      <p><strong>Recent context:</strong> news {ctx?.news?.length ?? 0}, corporate actions {ctx?.corporate_actions?.length ?? 0}, fundamentals {ctx?.fundamentals?.length ?? 0}</p>
    </section>
  );
}
