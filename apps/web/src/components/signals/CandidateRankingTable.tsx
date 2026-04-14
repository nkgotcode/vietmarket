import Link from 'next/link';

type CandidateRow = {
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
};

function pct(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export default function CandidateRankingTable({ rows }: { rows: CandidateRow[] }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Ticker</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Classification</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Score</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Confidence</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Bucket</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Trend / Momentum</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Liquidity</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker} style={{ background: row.blocking_flag ? '#fff8f8' : undefined }}>
              <td style={{ padding: '6px 4px' }}><Link href={`/app/ticker-state/${row.ticker}`}>{row.ticker}</Link></td>
              <td style={{ padding: '6px 4px' }}>
                <div>{row.sector ?? '—'}</div>
                <div style={{ color: '#666', fontSize: 12 }}>{row.industry_name ?? '—'}</div>
                <div style={{ color: '#888', fontSize: 11 }}>ICB {row.icb_code ?? '—'} • Industry {row.industry_code ?? '—'}</div>
              </td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.total_score.toFixed(2)}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.total_confidence)}</td>
              <td style={{ padding: '6px 4px' }}>{row.blocking_flag ? `${row.ranking_bucket} (blocked)` : row.ranking_bucket}</td>
              <td style={{ padding: '6px 4px' }}>{row.trend_state ?? '—'} / {row.momentum_state ?? '—'}</td>
              <td style={{ padding: '6px 4px' }}>{row.liquidity_bucket ?? '—'}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr><td colSpan={7} style={{ padding: '8px 4px', color: '#666' }}>No candidate rankings available.</td></tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
