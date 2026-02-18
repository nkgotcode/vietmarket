'use client';

import { useEffect, useMemo, useState } from 'react';
import { fetchLatest, fetchTopMovers, TF, LatestRow, TopMoverRow } from '@/lib/historyApi';

const TF_OPTIONS: TF[] = ['15m', '1h', '1d'];

function fmtPct(x: number | null | undefined) {
  if (x == null || !Number.isFinite(x)) return '—';
  const v = x * 100;
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function fmtTs(ms: number | null | undefined) {
  if (ms == null || !Number.isFinite(ms)) return '—';
  try {
    return new Date(ms).toISOString().replace('T', ' ').slice(0, 16) + 'Z';
  } catch {
    return String(ms);
  }
}

export default function MarketOverviewClient() {
  const [tf, setTf] = useState<TF>('15m');
  const [limitLatest, setLimitLatest] = useState<number>(50);
  const [limitMovers, setLimitMovers] = useState<number>(50);

  const [latest, setLatest] = useState<LatestRow[]>([]);
  const [movers, setMovers] = useState<TopMoverRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const title = useMemo(() => {
    if (tf === '15m') return 'Market overview (15m)';
    if (tf === '1h') return 'Market overview (1h)';
    return 'Market overview (1d)';
  }, [tf]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const [a, b] = await Promise.all([
          fetchLatest({ tf, limit: limitLatest }),
          fetchTopMovers({ tf, limit: limitMovers }),
        ]);
        if (cancelled) return;
        setLatest(a.rows);
        setMovers(b.rows);
      } catch (e: unknown) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setErr(msg);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tf, limitLatest, limitMovers]);

  return (
    <section style={{ marginTop: 24 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{title}</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            TF
            <select value={tf} onChange={(e) => setTf(e.target.value as TF)}>
              {TF_OPTIONS.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            Latest
            <input
              type="number"
              min={1}
              max={500}
              value={limitLatest}
              onChange={(e) => setLimitLatest(Math.max(1, Math.min(500, Number(e.target.value || 50))))}
              style={{ width: 90 }}
            />
          </label>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            Movers
            <input
              type="number"
              min={1}
              max={200}
              value={limitMovers}
              onChange={(e) => setLimitMovers(Math.max(1, Math.min(200, Number(e.target.value || 50))))}
              style={{ width: 90 }}
            />
          </label>
        </div>
      </div>

      {err ? (
        <p style={{ color: '#b00020' }}>{err}</p>
      ) : (
        <p style={{ color: '#666', marginTop: 8 }}>
          {loading ? 'Loading…' : `Latest snapshot (${latest.length}) • Top movers (${movers.length})`}
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Latest snapshot</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Ticker</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Close</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>TS</th>
                </tr>
              </thead>
              <tbody>
                {latest.map((r) => (
                  <tr key={`${r.ticker}:${r.tf}`}>
                    <td style={{ padding: '6px 4px' }}>{r.ticker}</td>
                    <td style={{ padding: '6px 4px', textAlign: 'right' }}>{r.c ?? '—'}</td>
                    <td style={{ padding: '6px 4px', textAlign: 'right', color: '#666' }}>{fmtTs(r.ts)}</td>
                  </tr>
                ))}
                {!loading && latest.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: '8px 4px', color: '#666' }}>
                      No data.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
          <h3 style={{ marginTop: 0 }}>Top movers</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Ticker</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Change</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Latest TS</th>
                </tr>
              </thead>
              <tbody>
                {movers.map((r) => (
                  <tr key={`${r.ticker}:${r.tf}`}>
                    <td style={{ padding: '6px 4px' }}>{r.ticker}</td>
                    <td style={{ padding: '6px 4px', textAlign: 'right' }}>{fmtPct(r.pct_change)}</td>
                    <td style={{ padding: '6px 4px', textAlign: 'right', color: '#666' }}>{fmtTs(r.ts_latest)}</td>
                  </tr>
                ))}
                {!loading && movers.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: '8px 4px', color: '#666' }}>
                      No data.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
