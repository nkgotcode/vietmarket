type FreshnessRow = {
  dataset_name: string;
  tf: string | null;
  freshness_seconds: number | null;
  freshness_status: string;
  max_event_ts: string | null;
  max_ingested_at: string | null;
};

export default function FreshnessGrid({ rows }: { rows: FreshnessRow[] }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <h3 style={{ marginTop: 0 }}>Dataset freshness</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Dataset</th>
              <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>TF</th>
              <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Status</th>
              <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Age (s)</th>
              <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Latest event</th>
              <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Latest ingested</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.dataset_name}:${row.tf ?? 'all'}`}>
                <td style={{ padding: '6px 4px' }}>{row.dataset_name}</td>
                <td style={{ padding: '6px 4px' }}>{row.tf ?? '—'}</td>
                <td style={{ padding: '6px 4px', textTransform: 'capitalize' }}>{row.freshness_status}</td>
                <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.freshness_seconds ?? '—'}</td>
                <td style={{ padding: '6px 4px' }}>{row.max_event_ts ?? '—'}</td>
                <td style={{ padding: '6px 4px' }}>{row.max_ingested_at ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}