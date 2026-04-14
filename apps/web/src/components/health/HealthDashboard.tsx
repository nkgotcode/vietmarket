'use client';

import { useEffect, useState } from 'react';

import FreshnessGrid from '@/components/health/FreshnessGrid';
import SystemStatusBanner from '@/components/health/SystemStatusBanner';
import WorkerHealthTable from '@/components/health/WorkerHealthTable';

type FreshnessRow = {
  dataset_name: string;
  ticker: string;
  tf: string;
  max_event_ts: string | null;
  max_ingested_at: string | null;
  freshness_seconds: number | null;
  freshness_status: string;
  freshness_context_json: Record<string, unknown>;
  updated_at: string;
};

type WorkerRun = {
  run_id: string;
  job_name: string;
  dataset_name: string | null;
  nomad_job_id: string | null;
  nomad_alloc_id: string | null;
  node_name: string | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  rows_read: number;
  rows_written: number;
  rows_upserted: number;
  warnings_count: number;
  errors_count: number;
  summary_json: Record<string, unknown>;
  created_at: string;
};

type WorkerFailure = {
  failure_id: string;
  run_id: string | null;
  job_name: string;
  stage: string | null;
  error_class: string;
  error_hash: string;
  error_message: string;
  retryable: boolean;
  created_at: string;
};

type HealthResponse = {
  snapshot: { overall_status: string } | null;
  issues: Array<{ issue_id: string; severity: string; issue_message: string; blocking: boolean; scope_key: string }>;
};

type FreshnessResponse = { rows: FreshnessRow[] };
type WorkersResponse = { runs: WorkerRun[]; failures: WorkerFailure[] };

export default function HealthDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [freshness, setFreshness] = useState<FreshnessResponse | null>(null);
  const [workers, setWorkers] = useState<WorkersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [a, b, c] = await Promise.all([
          fetch('/api/brain/health', { cache: 'no-store' }).then((r) => r.json()),
          fetch('/api/brain/freshness', { cache: 'no-store' }).then((r) => r.json()),
          fetch('/api/brain/workers', { cache: 'no-store' }).then((r) => r.json()),
        ]);
        if (cancelled) return;
        setHealth(a);
        setFreshness(b);
        setWorkers(c);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p style={{ color: '#b00020' }}>{error}</p>;
  if (!health || !freshness || !workers) return <p>Loading health…</p>;

  return (
    <section style={{ display: 'grid', gap: 16 }}>
      <SystemStatusBanner overallStatus={health.snapshot?.overall_status ?? 'unknown'} issueCount={health.issues.length} />
      <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Current issues</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          {health.issues.length === 0 ? <div style={{ color: '#666' }}>No current issues.</div> : null}
          {health.issues.map((issue) => (
            <div key={issue.issue_id} style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 8 }}>
              <strong style={{ textTransform: 'capitalize' }}>{issue.severity}</strong>
              <span style={{ marginLeft: 8 }}>{issue.scope_key}</span>
              <div>{issue.issue_message}</div>
            </div>
          ))}
        </div>
      </div>
      <FreshnessGrid rows={freshness.rows} />
      <WorkerHealthTable runs={workers.runs} failures={workers.failures} />
    </section>
  );
}