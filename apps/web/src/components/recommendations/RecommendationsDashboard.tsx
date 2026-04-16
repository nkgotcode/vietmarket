'use client';

import { useEffect, useState } from 'react';

import RecommendationCard from '@/components/recommendations/RecommendationCard';

type Payload = {
  ok: boolean;
  cycle: Record<string, unknown> | null;
  rows: Array<{
    ticker: string;
    status: string;
    analytical_state?: string | null;
    policy_blocked?: boolean;
    side: string;
    horizon: string;
    suggested_priority: number;
    summary: string;
    why_now: string;
    sector?: string | null;
    industry_name?: string | null;
    icb_code?: string | null;
    industry_code?: string | null;
    score_version?: string | null;
    paper_eligible?: boolean | null;
    opportunity_grade?: string | null;
    evidence_grade?: string | null;
    tradability_grade?: string | null;
    risk_containment_grade?: string | null;
    forecast_reliability?: number | null;
    evidence_reliability?: number | null;
    execution_reliability?: number | null;
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
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!payload) return <p>Loading recommendations…</p>;

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ color: '#666' }}>
        Recommendations now render explicit grade semantics: Opportunity Grade, Evidence Grade, Tradability Grade, Risk Containment Grade,
        plus Forecast Reliability, Evidence Reliability, and Execution Reliability. Analytical state remains visible even when policy blocks admission.
      </div>
      {payload.rows.map((row) => <RecommendationCard key={row.ticker} row={row} />)}
      {payload.rows.length === 0 ? <p style={{ color: '#666' }}>No recommendations available.</p> : null}
    </section>
  );
}
