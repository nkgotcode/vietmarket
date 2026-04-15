'use client';

import { useEffect, useState } from 'react';

import OperatorControlDashboard from '@/components/operator/OperatorControlDashboard';

type OperatorControlPayload = Parameters<typeof OperatorControlDashboard>[0]['data'];

export default function OperatorControlPage() {
  const [data, setData] = useState<OperatorControlPayload | null>(null);

  useEffect(() => {
    fetch('/api/brain/operator-control', { cache: 'no-store' })
      .then((r) => r.json() as Promise<OperatorControlPayload>)
      .then(setData);
  }, []);

  return (
    <main style={{ maxWidth: 1280, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Operator control</h1>
      <p style={{ color: '#6b7280', marginTop: 0 }}>
        Promotion policy state, gate results, and writable-primary verification live in one place.
      </p>
      {!data ? <p>Loading operator control…</p> : <OperatorControlDashboard data={data} />}
    </main>
  );
}
