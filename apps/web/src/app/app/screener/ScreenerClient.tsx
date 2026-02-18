'use client';

import { useEffect, useMemo, useState } from 'react';

type Row = {
  ticker: string;
  period: string;
  statement: string;
  period_date: string | null;
  metric: string;
  value: number | null;
};

const DEFAULTS = {
  metric: 'pe',
  period: 'Q',
  statement: 'ratio',
  min: '',
  max: '15',
  limit: '200',
};

export default function ScreenerClient() {
  const [metric, setMetric] = useState(DEFAULTS.metric);
  const [period, setPeriod] = useState(DEFAULTS.period);
  const [statement, setStatement] = useState(DEFAULTS.statement);
  const [min, setMin] = useState(DEFAULTS.min);
  const [max, setMax] = useState(DEFAULTS.max);
  const [limit, setLimit] = useState(DEFAULTS.limit);

  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const query = useMemo(() => ({ metric, period, statement, min, max, limit }), [metric, period, statement, min, max, limit]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const url = new URL('/api/history/fundamentals/screener', window.location.origin);
        url.searchParams.set('metric', query.metric);
        url.searchParams.set('period', query.period);
        url.searchParams.set('statement', query.statement);
        if (query.min) url.searchParams.set('min', query.min);
        if (query.max) url.searchParams.set('max', query.max);
        if (query.limit) url.searchParams.set('limit', query.limit);

        const r = await fetch(url.toString(), { cache: 'no-store' });
        if (!r.ok) throw new Error(await r.text());
        const j = await r.json();
        if (cancelled) return;
        setRows((j?.rows || []) as Row[]);
      } catch (e: unknown) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setErr(msg);
        setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <section style={{ marginTop: 12 }}>
      <h1 style={{ margin: '0 0 8px' }}>Screener</h1>
      <p style={{ color: '#666', marginTop: 0 }}>
        Powered by Simplize fi_latest (Timescale). This is a thin, honest UI for now.
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'end', padding: 12, border: '1px solid #eee', borderRadius: 8 }}>
        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Statement</span>
          <select value={statement} onChange={(e) => setStatement(e.target.value)}>
            <option value="ratio">ratio</option>
            <option value="is">is</option>
            <option value="bs">bs</option>
            <option value="cf">cf</option>
          </select>
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Period</span>
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="Q">Q</option>
            <option value="Y">Y</option>
          </select>
        </label>

        <label style={{ display: 'grid', gap: 4, minWidth: 180 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Metric</span>
          <input value={metric} onChange={(e) => setMetric(e.target.value)} placeholder="pe, roe, eps, ..." />
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Min</span>
          <input value={min} onChange={(e) => setMin(e.target.value)} placeholder="(none)" />
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Max</span>
          <input value={max} onChange={(e) => setMax(e.target.value)} placeholder="(none)" />
        </label>

        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Limit</span>
          <input value={limit} onChange={(e) => setLimit(e.target.value)} />
        </label>

        <div style={{ marginLeft: 'auto', color: '#666' }}>{loading ? 'Loading…' : `${rows.length} rows`}</div>
      </div>

      {err ? <p style={{ color: '#b00020' }}>{err}</p> : null}

      <div style={{ marginTop: 12, border: '1px solid #eee', borderRadius: 8, padding: 12, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Ticker</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Value</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: '6px 4px' }}>Period date</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.ticker}:${i}`}>
                <td style={{ padding: '6px 4px' }}>{r.ticker}</td>
                <td style={{ padding: '6px 4px', textAlign: 'right' }}>{r.value ?? '—'}</td>
                <td style={{ padding: '6px 4px', textAlign: 'right', color: '#666' }}>{r.period_date || '—'}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ padding: '8px 4px', color: '#666' }}>
                  No rows.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
