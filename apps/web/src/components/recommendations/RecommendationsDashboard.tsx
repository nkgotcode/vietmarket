'use client';

import { useEffect, useState } from 'react';

import RecommendationCard from '@/components/recommendations/RecommendationCard';

type Payload = {
  ok: boolean;
  cycle: Record<string, unknown> | null;
  rows: Array<{
    ticker: string;
    status: string;
    side: string;
    horizon: string;
    confidence: number;
    suggested_priority: number;
    summary: string;
    why_now: string;
    sector?: string | null;
    industry_name?: string | null;
    icb_code?: string | null;
    industry_code?: string | null;
    score_version?: string | null;
    alpha_score?: number | null;
    quality_score?: number | null;
    risk_score?: number | null;
    execution_score?: number | null;
    decision_score?: number | null;
    model_confidence?: number | null;
    evidence_confidence?: number | null;
    execution_confidence?: number | null;
    recommended_state?: string | null;
    paper_eligible?: boolean | null;
  }>;
};

export default function RecommendationsDashboard() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await fetch('/api/brain/recommendations', { cache: 'no-store' }).then((r) => r.json() as Promise<Payload>);
        if (cancelled) return;
        setPayload(result);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load recommendations');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!payload) return <p>Loading recommendations…</p>;

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ color: '#666' }}>Durable recommendation objects now prefer scoring v2 decision states and explicit promotion semantics over legacy Phase 3 bucket labels.</div>
      {payload.rows.map((row) => <RecommendationCard key={row.ticker} row={row} />)}
      {payload.rows.length === 0 ? <p style={{ color: '#666' }}>No recommendations available.</p> : null}
    </section>
  );
}
