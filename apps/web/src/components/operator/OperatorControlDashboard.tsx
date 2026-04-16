'use client';

import type { ReactNode } from 'react';

type OperatorControlPayload = {
  ok: boolean;
  cycle: {
    cycle_id: string;
    regime_code: string | null;
    overall_status: string;
    freshness_status: string;
    created_at: string;
  } | null;
  db_target: {
    database_name: string;
    current_user: string;
    transaction_read_only: string;
    in_recovery: boolean;
    writable_primary: boolean;
    server_addr: string | null;
    server_port: number;
    postgres_version: string;
    observed_at: string;
  } | null;
  active_policy: {
    promotion_policy_version: string;
    status: string;
    paper_trading_enabled: boolean;
    thresholds_json: Record<string, unknown> | null;
    notes_json: Record<string, unknown> | null;
    created_at: string;
  } | null;
  latest_gate_run: {
    run_id: string;
    status: string;
    rows_written: number;
    rows_upserted: number;
    started_at: string;
    finished_at: string | null;
    summary_json: Record<string, unknown> | null;
  } | null;
  admissions: {
    counts: Record<string, number>;
    total: number;
    rows: Array<{
      admission_status: string;
      ticker: string;
      score_version: string;
      promotion_policy_version: string;
      policy_result: string | null;
      paper_trading_enabled: boolean;
      admission_json: Record<string, unknown> | null;
      created_at: string;
      promotion_state: string | null;
      paper_eligible: boolean;
      analytical_state?: string | null;
      policy_blocked?: boolean;
      opportunity_grade: string;
      tradability_grade: string;
      forecast_reliability: number;
      execution_reliability: number;
    }>;
  };
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

function pct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export default function OperatorControlDashboard({ data }: { data: OperatorControlPayload }) {
  const admissionEntries = Object.entries(data.admissions.counts);
  const previewRows = data.admissions.rows.slice(0, 20);

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div
        style={{
          padding: 12,
          borderRadius: 12,
          background: data.db_target?.writable_primary ? '#dcfce7' : '#fee2e2',
          color: data.db_target?.writable_primary ? '#166534' : '#991b1b',
          fontWeight: 600,
        }}
      >
        {data.db_target?.writable_primary
          ? 'Writable primary confirmed. Live write-path verification can run against this target.'
          : 'Current DB target is not a writable primary. Do not run live migrations or supervisor write-path verification against it yet.'}
      </div>

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <Card title="DB target">
          {data.db_target ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Metric label="Writable primary" value={data.db_target.writable_primary ? 'yes' : 'no'} />
              <Metric label="Read only" value={data.db_target.transaction_read_only} />
              <Metric label="In recovery" value={data.db_target.in_recovery ? 'yes' : 'no'} />
              <div style={{ fontSize: 14, color: '#4b5563' }}>
                {data.db_target.database_name} @ {data.db_target.server_addr ?? 'unknown'}:{data.db_target.server_port}
              </div>
            </div>
          ) : (
            <p>No DB status available.</p>
          )}
        </Card>

        <Card title="Active promotion policy">
          {data.active_policy ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Metric label="Version" value={data.active_policy.promotion_policy_version} />
              <Metric label="Policy status" value={data.active_policy.status} />
              <Metric label="Paper trading enabled" value={data.active_policy.paper_trading_enabled ? 'yes' : 'no'} />
            </div>
          ) : (
            <p>No promotion policy row yet.</p>
          )}
        </Card>

        <Card title="Promotion gate run">
          {data.latest_gate_run ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <Metric label="Status" value={data.latest_gate_run.status} />
              <Metric label="Rows written" value={String(data.latest_gate_run.rows_written)} />
              <Metric label="Rows upserted" value={String(data.latest_gate_run.rows_upserted)} />
            </div>
          ) : (
            <p>No gate run yet.</p>
          )}
        </Card>

        <Card title="Admissions summary">
          <div style={{ display: 'grid', gap: 12 }}>
            <Metric label="Latest cycle" value={data.cycle?.cycle_id ?? 'n/a'} />
            <Metric label="Admission rows" value={String(data.admissions.total)} />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {admissionEntries.map(([status, count]) => (
                <span key={status} style={{ padding: '6px 10px', borderRadius: 999, background: '#f3f4f6' }}>
                  {status}: {count}
                </span>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <Card title="Promotion thresholds">
        {data.active_policy?.thresholds_json ? (
          <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#f8fafc', overflowX: 'auto', fontSize: 12 }}>
            {JSON.stringify(data.active_policy.thresholds_json, null, 2)}
          </pre>
        ) : (
          <p>No threshold payload found.</p>
        )}
      </Card>

      <Card title="Admission preview">
        {previewRows.length === 0 ? (
          <p>No paper trade admissions yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Ticker</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Admission</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Analytical state</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Grades</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Reliability</th>
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row) => (
                <tr key={`${row.ticker}-${row.created_at}`}>
                  <td style={{ paddingTop: 10, verticalAlign: 'top' }}>{row.ticker}</td>
                  <td style={{ paddingTop: 10, verticalAlign: 'top' }}>
                    <strong>{row.admission_status}</strong>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>{row.policy_result ?? 'no policy result'}</div>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>policy blocked: {row.policy_blocked ? 'yes' : 'no'}</div>
                  </td>
                  <td style={{ paddingTop: 10, verticalAlign: 'top' }}>
                    {row.analytical_state ?? row.promotion_state ?? 'n/a'}
                    <div style={{ color: '#6b7280', fontSize: 12 }}>paper eligible: {row.paper_eligible ? 'yes' : 'no'}</div>
                  </td>
                  <td style={{ paddingTop: 10, verticalAlign: 'top' }}>
                    <div>Opportunity Grade: {row.opportunity_grade}</div>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>Tradability Grade: {row.tradability_grade}</div>
                  </td>
                  <td style={{ paddingTop: 10, verticalAlign: 'top' }}>
                    <div>Forecast Reliability: {pct(row.forecast_reliability)}</div>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>Execution Reliability: {pct(row.execution_reliability)}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
