type WorkerRun = {
  run_id: string;
  job_name: string;
  node_name: string | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  rows_written: number;
  rows_upserted: number;
};

type WorkerFailure = {
  failure_id: string;
  job_name: string;
  stage: string | null;
  error_class: string;
  error_message: string;
  created_at: string;
};

export default function WorkerHealthTable({ runs, failures }: { runs: WorkerRun[]; failures: WorkerFailure[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Recent worker runs</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Job</th>
                <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Node</th>
                <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Rows</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td style={{ padding: '6px 4px' }}>{run.job_name}</td>
                  <td style={{ padding: '6px 4px' }}>{run.status}</td>
                  <td style={{ padding: '6px 4px' }}>{run.node_name ?? '—'}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'right' }}>{run.rows_upserted || run.rows_written || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Recent worker failures</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          {failures.length === 0 ? <div style={{ color: '#666' }}>No failures recorded.</div> : null}
          {failures.map((failure) => (
            <div key={failure.failure_id} style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 8 }}>
              <strong>{failure.job_name}</strong>
              <div style={{ color: '#666', fontSize: 12 }}>{failure.stage ?? 'unknown-stage'} • {failure.error_class}</div>
              <div style={{ fontSize: 13 }}>{failure.error_message}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}