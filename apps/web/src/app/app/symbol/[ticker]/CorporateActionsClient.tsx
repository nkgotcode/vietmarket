'use client';

import { useEffect, useState } from 'react';

type Row = {
  id: string;
  ticker: string;
  exchange: string | null;
  ex_date: string | null;
  record_date: string | null;
  pay_date: string | null;
  headline: string | null;
  event_type: string | null;
  source_url: string | null;
};

type Cursor = { beforeExDate: string; beforeId: string };

const INDEX_SET = new Set(['VNINDEX', 'HNXINDEX', 'UPCOMINDEX']);

export default function CorporateActionsClient({ ticker }: { ticker: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [cursor, setCursor] = useState<Cursor | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const isIndex = INDEX_SET.has(ticker);

  async function loadMore(reset = false) {
    setLoading(true);
    setErr(null);
    try {
      const url = new URL('/api/history/corporate-actions/by-ticker', window.location.origin);
      url.searchParams.set('ticker', ticker);
      url.searchParams.set('limit', '25');
      const c = reset ? null : cursor;
      if (c) {
        url.searchParams.set('beforeExDate', c.beforeExDate);
        url.searchParams.set('beforeId', c.beforeId);
      }

      const r = await fetch(url.toString(), { cache: 'no-store' });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      const newRows = (j?.rows || []) as Row[];
      const next = j?.nextCursor || null;

      setRows((prev) => (reset ? newRows : [...prev, ...newRows]));
      setCursor(next);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setRows([]);
    setCursor(null);
    if (isIndex) return;
    loadMore(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  return (
    <section style={{ marginTop: 22 }}>
      <h2 style={{ margin: '0 0 8px' }}>Corporate actions & dividends</h2>
      {isIndex ? (
        <p style={{ color: '#666', marginTop: 0 }}>Not applicable to indices.</p>
      ) : (
        <p style={{ color: '#666', marginTop: 0 }}>{loading ? 'Loading…' : `${rows.length} events`}</p>
      )}
      {err ? <p style={{ color: '#b00020' }}>{err}</p> : null}

      {!isIndex ? (
        <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {rows.map((r) => (
              <li key={r.id} style={{ marginBottom: 8 }}>
                <div>
                  <strong>{r.ex_date || '—'}</strong> {r.event_type ? <span style={{ color: '#666' }}>({r.event_type})</span> : null}
                </div>
                <div style={{ color: '#333' }}>{r.headline || '—'}</div>
                <div style={{ color: '#666', fontSize: 12 }}>
                  {r.record_date ? `Record: ${r.record_date}` : ''}{r.pay_date ? ` · Pay: ${r.pay_date}` : ''}
                  {r.source_url ? (
                    <> · <a href={r.source_url} target="_blank" rel="noreferrer">source</a></>
                  ) : null}
                </div>
              </li>
            ))}
            {!loading && rows.length === 0 ? <li style={{ color: '#666' }}>No events found.</li> : null}
          </ul>

          <button
            onClick={() => loadMore(false)}
            disabled={loading || !cursor}
            style={{ marginTop: 10, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 8, background: '#fff' }}
          >
            {cursor ? (loading ? 'Loading…' : 'Load more') : 'No more'}
          </button>
        </div>
      ) : null}
    </section>
  );
}
