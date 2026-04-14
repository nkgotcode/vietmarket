'use client';

import { useEffect, useState } from 'react';

type BriefPayload = {
  ok: boolean;
  brief: {
    title: string;
    summary_text: string;
    brief_json?: Record<string, unknown> | null;
    cycle_id: string;
    created_at: string;
  } | null;
};

export default function BriefingPage() {
  const [payload, setPayload] = useState<BriefPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await fetch('/api/brain/daily-brief', { cache: 'no-store' }).then((r) => r.json() as Promise<BriefPayload>);
        if (cancelled) return;
        setPayload(result);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load daily brief');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Briefing</h1>
      {error ? <p style={{ color: '#b00020' }}>{error}</p> : null}
      {!payload ? <p>Loading briefing…</p> : null}
      {payload?.brief ? (
        <section style={{ display: 'grid', gap: 12, border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
          <h2 style={{ margin: 0 }}>{payload.brief.title}</h2>
          <div style={{ color: '#666' }}>{payload.brief.summary_text}</div>
          <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>
            {JSON.stringify(payload.brief.brief_json ?? {}, null, 2)}
          </pre>
        </section>
      ) : null}
    </main>
  );
}
