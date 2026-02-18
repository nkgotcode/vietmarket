'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchNewsLatest, NewsRow } from '@/lib/historyApi';

function fmtTime(s: string | null | undefined) {
  if (!s) return '—';
  try {
    // show YYYY-MM-DD HH:MM (UTC)
    return new Date(s).toISOString().replace('T', ' ').slice(0, 16) + 'Z';
  } catch {
    return s;
  }
}

export default function HeadlinesClient() {
  const [rows, setRows] = useState<NewsRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const r = await fetchNewsLatest({ limit: 30 });
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
  }, []);

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ margin: 0 }}>Headlines</h2>
      <p style={{ color: '#666', marginTop: 8 }}>{loading ? 'Loading…' : `Latest ${rows.length} articles`}</p>
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
                {a.tickers?.length ? (
                  <>
                    {' '}
                    •{' '}
                    {a.tickers.slice(0, 6).map((t) => (
                      <Link key={t} href={`/app/symbol/${t}`} style={{ marginRight: 8 }}>
                        {t}
                      </Link>
                    ))}
                  </>
                ) : null}
              </div>
              {a.snippet ? <div style={{ color: '#444', fontSize: 13, marginTop: 4 }}>{a.snippet}</div> : null}
            </li>
          ))}
          {!loading && rows.length === 0 ? <li style={{ color: '#666' }}>No articles.</li> : null}
        </ul>
      </div>
    </section>
  );
}
