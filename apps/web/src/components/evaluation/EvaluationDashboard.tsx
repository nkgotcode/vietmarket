'use client';

import type { ReactNode } from 'react';

type EvaluationPayload = {
  ok: boolean;
  latest_run: {
    supervisor_run_id: string;
    mode: string;
    status: string;
    latest_health_status: string | null;
    latest_cycle_id: string | null;
    started_at: string;
    finished_at: string | null;
  } | null;
  outcomes: {
    counts: Record<string, number>;
    total: number;
    positive_rate: number;
  };
  portfolio: {
    cycle_id: string;
    cash_balance: number;
    market_value: number;
    unrealized_pnl: number;
    realized_pnl: number;
    positions_count: number;
    equity: number;
    created_at: string;
  } | null;
  calibration: Array<{
    metric_name: string;
    metric_value: number;
    metric_json: unknown;
    updated_at: string;
  }>;
  replay: {
    run: {
      replay_run_id: string;
      cycle_id: string;
      replay_scope: string;
      created_at: string;
    } | null;
    rows: Array<{
      ticker: string;
      result_json: { total_score?: number; ranking_bucket?: string };
      created_at: string;
    }>;
  };
  prompts: Array<{ prompt_name: string; prompt_version: string; updated_at: string }>;
  model_runs: Array<{ model_run_id: string; cycle_id: string | null; run_kind: string; model_name: string; created_at: string }>;
  labels_coverage: Array<{ horizon_days: number; row_count: number; avg_forward_return: number; avg_excess_return: number }>;
  calibration_run: { calibration_run_id: string; score_version: string; scope: string; created_at: string } | null;
  calibration_buckets: Array<{ bucket_name: string; horizon_days: number; sample_size: number; avg_forward_return: number; median_forward_return: number; positive_rate: number; avg_excess_return: number; avg_max_drawdown: number; created_at: string }>;
  cohort_metrics: Array<{ cohort_type: string; cohort_key: string; horizon_days: number; sample_size: number; positive_rate: number; avg_forward_return: number; median_forward_return: number; avg_excess_return: number; avg_max_drawdown: number; created_at: string }>;
  grade_versions: Array<{ grade_version: string; status: string; description: string; created_at: string }>;
  grade_preview: Array<{
    grade_version: string;
    ticker: string;
    analytical_state: string;
    final_state: string;
    paper_eligible: boolean;
    policy_blocked: boolean;
    forecast_reliability: number;
    evidence_reliability: number;
    execution_reliability: number;
    opportunity_grade: string;
    evidence_grade: string;
    tradability_grade: string;
    risk_containment_grade: string;
    created_at: string;
  }>;
};

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff' }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function EvaluationDashboard({ data }: { data: EvaluationPayload }) {
  const outcomeEntries = Object.entries(data.outcomes.counts);
  const bucketPreview = data.calibration_buckets.slice(0, 12);
  const cohortPreview = data.cohort_metrics.slice(0, 16);
  const gradePreview = data.grade_preview.slice(0, 12);

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ padding: 12, borderRadius: 12, background: '#fef3c7', color: '#92400e', fontWeight: 600 }}>
        Evaluation now centers the grade plane: analytical state, policy visibility, explicit grade labels, and labeled reliability dimensions.
      </div>

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <Card title="Latest supervisor run">
          {data.latest_run ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Metric label="Status" value={data.latest_run.status} />
              <Metric label="Health" value={data.latest_run.latest_health_status ?? 'unknown'} />
              <Metric label="Cycle" value={data.latest_run.latest_cycle_id ?? 'n/a'} />
            </div>
          ) : <p>No supervisor run yet.</p>}
        </Card>
        <Card title="Recommendation outcomes">
          <div style={{ display: 'grid', gap: 12 }}>
            <Metric label="Total outcomes" value={String(data.outcomes.total)} />
            <Metric label="Positive rate" value={`${(data.outcomes.positive_rate * 100).toFixed(1)}%`} />
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {outcomeEntries.map(([label, count]) => <span key={label} style={{ padding: '6px 10px', borderRadius: 999, background: '#f3f4f6' }}>{label}: {count}</span>)}
            </div>
          </div>
        </Card>
        <Card title="Paper portfolio snapshot">
          {data.portfolio ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Metric label="Equity" value={data.portfolio.equity.toFixed(0)} />
              <Metric label="Positions" value={String(data.portfolio.positions_count)} />
              <Metric label="Unrealized PnL" value={data.portfolio.unrealized_pnl.toFixed(0)} />
            </div>
          ) : <p>No portfolio snapshot yet.</p>}
        </Card>
      </div>

      <Card title="Forward-label coverage">
        {data.labels_coverage.length === 0 ? <p>No forward labels yet.</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Horizon</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Rows</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Avg forward return</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Avg excess return</th></tr></thead>
            <tbody>
              {data.labels_coverage.map((row) => (
                <tr key={row.horizon_days}><td style={{ paddingTop: 10 }}>{row.horizon_days}d</td><td style={{ paddingTop: 10 }}>{row.row_count}</td><td style={{ paddingTop: 10 }}>{(row.avg_forward_return * 100).toFixed(2)}%</td><td style={{ paddingTop: 10 }}>{(row.avg_excess_return * 100).toFixed(2)}%</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Calibration metrics">
        {data.calibration.length === 0 ? <p>No calibration metrics yet.</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Metric</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Value</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Updated</th></tr></thead>
            <tbody>
              {data.calibration.map((row) => (
                <tr key={row.metric_name}><td style={{ paddingTop: 10 }}>{row.metric_name}</td><td style={{ paddingTop: 10 }}>{row.metric_value.toFixed(4)}</td><td style={{ paddingTop: 10 }}>{row.updated_at}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Calibration buckets">
        {bucketPreview.length === 0 ? <p>No calibration buckets yet.</p> : (
          <div style={{ display: 'grid', gap: 8 }}>
            {data.calibration_run ? <p style={{ margin: 0 }}>Run {data.calibration_run.calibration_run_id} — {data.calibration_run.score_version}</p> : null}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Bucket</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Horizon</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>N</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Avg return</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Positive rate</th></tr></thead>
              <tbody>
                {bucketPreview.map((row) => (
                  <tr key={`${row.bucket_name}-${row.horizon_days}`}><td style={{ paddingTop: 10 }}>{row.bucket_name}</td><td style={{ paddingTop: 10 }}>{row.horizon_days}d</td><td style={{ paddingTop: 10 }}>{row.sample_size}</td><td style={{ paddingTop: 10 }}>{(row.avg_forward_return * 100).toFixed(2)}%</td><td style={{ paddingTop: 10 }}>{(row.positive_rate * 100).toFixed(1)}%</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Grade plane preview">
        {gradePreview.length === 0 ? <p>No grade preview rows yet.</p> : (
          <div style={{ display: 'grid', gap: 8 }}>
            <p style={{ margin: 0 }}>Latest grade versions: {data.grade_versions.map((row) => row.grade_version).join(', ')}</p>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Ticker</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>State</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Opportunity Grade</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Tradability Grade</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Forecast Reliability</th>
                </tr>
              </thead>
              <tbody>
                {gradePreview.map((row) => (
                  <tr key={`${row.grade_version}-${row.ticker}`}>
                    <td style={{ paddingTop: 10 }}>{row.ticker}</td>
                    <td style={{ paddingTop: 10 }}>{row.final_state}{row.paper_eligible ? ' ✅' : ''}<div style={{ color: '#6b7280', fontSize: 12 }}>analytical {row.analytical_state} • policy blocked {row.policy_blocked ? 'yes' : 'no'}</div></td>
                    <td style={{ paddingTop: 10 }}>{row.opportunity_grade}<div style={{ color: '#6b7280', fontSize: 12 }}>Evidence Grade {row.evidence_grade}</div></td>
                    <td style={{ paddingTop: 10 }}>{row.tradability_grade}<div style={{ color: '#6b7280', fontSize: 12 }}>Risk Containment Grade {row.risk_containment_grade}</div></td>
                    <td style={{ paddingTop: 10 }}>{pct(row.forecast_reliability)}<div style={{ color: '#6b7280', fontSize: 12 }}>Execution Reliability {pct(row.execution_reliability)}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Regime and liquidity cohorts">
        {cohortPreview.length === 0 ? <p>No cohort metrics yet.</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Type</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Cohort</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Horizon</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>N</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Avg return</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Positive rate</th></tr></thead>
            <tbody>
              {cohortPreview.map((row, idx) => (
                <tr key={`${row.cohort_type}-${row.cohort_key}-${row.horizon_days}-${idx}`}><td style={{ paddingTop: 10 }}>{row.cohort_type}</td><td style={{ paddingTop: 10 }}>{row.cohort_key}</td><td style={{ paddingTop: 10 }}>{row.horizon_days}d</td><td style={{ paddingTop: 10 }}>{row.sample_size}</td><td style={{ paddingTop: 10 }}>{(row.avg_forward_return * 100).toFixed(2)}%</td><td style={{ paddingTop: 10 }}>{(row.positive_rate * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Latest replay">
        {data.replay.run ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <p style={{ margin: 0 }}>Replay run {data.replay.run.replay_run_id} for cycle {data.replay.run.cycle_id}</p>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Ticker</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Total score</th><th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Bucket</th></tr></thead>
              <tbody>
                {data.replay.rows.map((row) => (
                  <tr key={row.ticker}><td style={{ paddingTop: 10 }}>{row.ticker}</td><td style={{ paddingTop: 10 }}>{Number(row.result_json?.total_score ?? 0).toFixed(2)}</td><td style={{ paddingTop: 10 }}>{row.result_json?.ranking_bucket ?? 'n/a'}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No replay run yet.</p>}
      </Card>

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <Card title="Prompt registry">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.prompts.map((row) => <li key={row.prompt_name}>{row.prompt_name} — {row.prompt_version}</li>)}
          </ul>
        </Card>
        <Card title="Model runs">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.model_runs.map((row) => <li key={row.model_run_id}>{row.run_kind} — {row.model_name} — {row.created_at}</li>)}
          </ul>
        </Card>
      </div>
    </div>
  );
}
