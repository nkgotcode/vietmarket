'use client';

import { useEffect, useState } from 'react';
import EvaluationDashboard from '@/components/evaluation/EvaluationDashboard';

type EvaluationPayload = Parameters<typeof EvaluationDashboard>[0]['data'];

export default function EvaluationPage() {
  const [data, setData] = useState<EvaluationPayload | null>(null);

  useEffect(() => {
    fetch('/api/brain/evaluation', { cache: 'no-store' })
      .then((r) => r.json() as Promise<EvaluationPayload>)
      .then(setData);
  }, []);

  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Evaluation</h1>
      {!data ? <p>Loading evaluation scorecard…</p> : <EvaluationDashboard data={data} />}
    </main>
  );
}
