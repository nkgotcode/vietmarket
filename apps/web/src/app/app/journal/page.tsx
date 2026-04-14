'use client';

import { useEffect, useState } from 'react';

export default function JournalPage() {
  const [data, setData] = useState<{ ok: boolean; rows: Array<Record<string, unknown>> } | null>(null);
  useEffect(() => { fetch('/api/brain/journal', { cache: 'no-store' }).then((r)=>r.json()).then(setData); }, []);
  return <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}><h1 style={{ marginTop: 0 }}>Decision journal</h1>{!data ? <p>Loading journal…</p> : <pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(data.rows, null, 2)}</pre>}</main>;
}
