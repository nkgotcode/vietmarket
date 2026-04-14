type Row = {
  sector: string;
  names_count: number;
  adv_count: number;
  dec_count: number;
  breadth_pct: number | null;
  avg_ret_1d: number | null;
  avg_ret_5d: number | null;
};

function pct(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

export default function SectorTable({ rows }: { rows: Row[] }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Sector</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Names</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Adv</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Dec</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Breadth</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Avg 1D</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Avg 5D</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.sector}>
              <td style={{ padding: '6px 4px' }}>{row.sector}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.names_count}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.adv_count}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.dec_count}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.breadth_pct)}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.avg_ret_1d)}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.avg_ret_5d)}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7} style={{ padding: '8px 4px', color: '#666' }}>No sector rows available.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
