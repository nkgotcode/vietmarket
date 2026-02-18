'use client';

import { useEffect, useState } from 'react';

type Row = {
  ticker: string;
  period: string;
  statement: string;
  period_date: string | null;
  metric: string;
  value: number | null;
};

export default function FundamentalsClient({ ticker }: { ticker: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const url = new URL('/api/history/fundamentals/latest', window.location.origin);
        url.searchParams.set('ticker', ticker);
        url.searchParams.set('period', 'Q');
        url.searchParams.set('limit', '200');

        const r = await fetch(url.toString(), { cache: 'no-store' });
        if (!r.ok) throw new Error(await r.text());
        const j = await r.json();
        if (cancelled) return;
        setRows((j?.rows || []) as Row[]);
      } catch (e: unknown) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setErr(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return (
    <section style={{ marginTop: 22 }}>
      <h2 style={{ margin: '0 0 8px' }}>Fundamentals (Simplize)</h2>
      <p style={{ color: '#666', marginTop: 0 }}>{loading ? 'Loading…' : `${rows.length} metrics`}</p>
      {err ? <p style={{ color: '#b00020' }}>{err}</p> : null}

      <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Statement</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Metric</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Value</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Period</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.statement}:${r.metric}:${i}`}>
                <td style={{ padding: '6px 4px' }}>{r.statement}</td>
                <td style={{ padding: '6px 4px' }}>{r.metric}</td>
                <td style={{ padding: '6px 4px', textAlign: 'right' }}>{r.value ?? '—'}</td>
                <td style={{ padding: '6px 4px', textAlign: 'right', color: '#666' }}>{r.period_date || '—'}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ padding: '8px 4px', color: '#666' }}>
                  No fundamentals found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
