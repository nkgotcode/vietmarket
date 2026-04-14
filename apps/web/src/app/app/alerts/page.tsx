'use client';

import { useEffect, useState } from 'react';

export default function AlertsPage() {
  const [data, setData] = useState<{ ok: boolean; health: Record<string, unknown> | null; rows: Array<Record<string, unknown>> } | null>(null);
  useEffect(() => { fetch('/api/brain/alerts', { cache: 'no-store' }).then((r)=>r.json()).then(setData); }, []);
  return <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}><h1 style={{ marginTop: 0 }}>Alerts</h1>{!data ? <p>Loading alerts…</p> : <section style={{display:'grid',gap:12}}><pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(data.health, null, 2)}</pre><pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(data.rows, null, 2)}</pre></section>}</main>;
}
