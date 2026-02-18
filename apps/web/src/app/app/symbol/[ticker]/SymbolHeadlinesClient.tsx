'use client';

import { useEffect, useState } from 'react';
import { fetchNewsByTicker, NewsRow } from '@/lib/historyApi';

function fmtTime(s: string | null | undefined) {
  if (!s) return '—';
  try {
    return new Date(s).toISOString().replace('T', ' ').slice(0, 16) + 'Z';
  } catch {
    return s;
  }
}

export default function SymbolHeadlinesClient({ ticker }: { ticker: string }) {
  const [rows, setRows] = useState<NewsRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const r = await fetchNewsByTicker({ ticker, limit: 25 });
        if (cancelled) return;
        setRows(r.rows);
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
      <h2 style={{ margin: '0 0 8px' }}>News</h2>
      <p style={{ color: '#666', marginTop: 0 }}>{loading ? 'Loading…' : `${rows.length} articles`}</p>
      {err ? <p style={{ color: '#b00020' }}>{err}</p> : null}

      <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {rows.map((a) => (
            <li key={a.url} style={{ margin: '8px 0' }}>
              <a href={a.url} target="_blank" rel="noreferrer" style={{ fontWeight: 600 }}>
                {a.title}
              </a>
              <div style={{ color: '#666', fontSize: 12, marginTop: 2 }}>
                {a.source} • {fmtTime(a.published_at)}
              </div>
              {a.snippet ? <div style={{ color: '#444', fontSize: 13, marginTop: 4 }}>{a.snippet}</div> : null}
            </li>
          ))}
          {!loading && rows.length === 0 ? <li style={{ color: '#666' }}>No articles for {ticker}.</li> : null}
        </ul>
      </div>
    </section>
  );
}
