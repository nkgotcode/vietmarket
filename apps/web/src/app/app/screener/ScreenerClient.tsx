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

const PRESETS: Array<{ label: string; statement: string; metric: string; min?: string; max?: string }> = [
  { label: 'P/E', statement: 'kpi', metric: 'pe' },
  { label: 'P/B', statement: 'kpi', metric: 'pb' },
  { label: 'EV/EBITDA', statement: 'kpi', metric: 'evEbitda' },
  { label: 'ROE', statement: 'kpi', metric: 'returnOnEquity', min: '0.15' },
  { label: 'ROA', statement: 'kpi', metric: 'returnOnAssets', min: '0.05' },
  { label: 'Gross margin', statement: 'kpi', metric: 'grossMargin', min: '0.15' },
  { label: 'Net margin', statement: 'kpi', metric: 'netMargin', min: '0.08' },
  { label: 'D/E (net)', statement: 'kpi', metric: 'netDebtEquityRatio', max: '1.5' },
  { label: 'D/E (liabilities)', statement: 'kpi', metric: 'liabilitiesToEquity', max: '2.0' },
  { label: 'Interest coverage', statement: 'kpi', metric: 'interestCoverageRatio', min: '3' },
  { label: 'Current ratio', statement: 'kpi', metric: 'currentRatio', min: '1' },
];

const DEFAULTS = {
  metric: 'returnOnEquity',
  period: 'Q',
  statement: 'kpi',
  min: '0.15',
  max: '',
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
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, width: '100%' }}>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => {
                setStatement(p.statement);
                setMetric(p.metric);
                setMin(p.min ?? '');
                setMax(p.max ?? '');
              }}
              style={{
                border: '1px solid #ddd',
                background: '#fff',
                padding: '6px 10px',
                borderRadius: 999,
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
        <label style={{ display: 'grid', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666' }}>Statement</span>
          <select value={statement} onChange={(e) => setStatement(e.target.value)}>
            <option value="kpi">kpi (named metrics)</option>
            <option value="ratio">ratio (coded)</option>
            <option value="is">is (coded)</option>
            <option value="bs">bs (coded)</option>
            <option value="cf">cf (coded)</option>
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
