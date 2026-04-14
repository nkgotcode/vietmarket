'use client';

import { useEffect, useState } from 'react';

export default function SystemPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [regime, setRegime] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    Promise.all([
      fetch('/api/brain/health', { cache: 'no-store' }).then((r)=>r.json()),
      fetch('/api/brain/regime', { cache: 'no-store' }).then((r)=>r.json()),
    ]).then(([h,rg]) => { setHealth(h); setRegime(rg); });
  }, []);
  return <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}><h1 style={{ marginTop: 0 }}>System</h1>{!health || !regime ? <p>Loading system…</p> : <section style={{display:'grid',gap:12}}><pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(health, null, 2)}</pre><pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(regime, null, 2)}</pre></section>}</main>;
}
