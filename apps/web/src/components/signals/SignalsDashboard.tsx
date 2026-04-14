'use client';

import { useEffect, useState } from 'react';

import CandidateRankingTable from '@/components/signals/CandidateRankingTable';
import SignalBreakdownTable from '@/components/signals/SignalBreakdownTable';

type CandidatePayload = {
  ok: boolean;
  cycle: Record<string, unknown> | null;
  rows: Array<{
    ticker: string;
    sector: string | null;
    industry_name: string | null;
    icb_code: string | null;
    industry_code: string | null;
    total_score: number;
    total_confidence: number;
    ranking_bucket: string;
    blocking_flag: boolean;
    trend_state: string | null;
    momentum_state: string | null;
    liquidity_bucket: string | null;
  }>;
};

type SignalsPayload = {
  ok: boolean;
  cycle: Record<string, unknown> | null;
  rows: Array<{
    ticker: string;
    sector: string | null;
    industry_name: string | null;
    ranking_bucket: string;
    total_score: number;
    total_confidence: number;
    signals: Array<{
      signal_family: string;
      score_raw: number;
      score_normalized: number;
      confidence: number;
      blocking_flag: boolean;
      horizon: string;
      components: Array<{
        component_name: string;
        component_value: number | null;
        component_weight: number | null;
        component_note: string | null;
      }>;
    }>;
  }>;
};

export default function SignalsDashboard() {
  const [candidatePayload, setCandidatePayload] = useState<CandidatePayload | null>(null);
  const [signalPayload, setSignalPayload] = useState<SignalsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [candidateResult, signalResult] = await Promise.all([
          fetch('/api/brain/candidates', { cache: 'no-store' }).then((r) => r.json() as Promise<CandidatePayload>),
          fetch('/api/brain/signals', { cache: 'no-store' }).then((r) => r.json() as Promise<SignalsPayload>),
        ]);
        if (cancelled) return;
        setCandidatePayload(candidateResult);
        setSignalPayload(signalResult);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load Phase 3 signal engine');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!candidatePayload || !signalPayload) return <p>Loading signal engine…</p>;

  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <div style={{ color: '#666' }}>
        Deterministic Phase 3 candidate rankings and family-level signal explanations from the latest market-state cycle.
      </div>
      <div>
        <h3 style={{ marginBottom: 8 }}>Ranked candidates</h3>
        <CandidateRankingTable rows={candidatePayload.rows} />
      </div>
      <div>
        <h3 style={{ marginBottom: 8 }}>Signal breakdowns</h3>
        <SignalBreakdownTable rows={signalPayload.rows} />
      </div>
    </section>
  );
}
