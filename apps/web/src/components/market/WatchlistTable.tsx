import Link from 'next/link';

type Row = {
  ticker: string;
  sector: string | null;
  industry_name: string | null;
  icb_code: string | null;
  industry_code: string | null;
  price_last: number | null;
  ret_1d: number | null;
  ret_5d: number | null;
  watchlist_score: number;
  trend_state: string;
  momentum_state: string;
  liquidity_bucket: string;
  article_count_24h: number;
  classification_source?: string | null;
};

function pct(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

export default function WatchlistTable({ rows }: { rows: Row[] }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Ticker</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Sector / industry</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Price</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>1D</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>5D</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Trend / momentum</th>
            <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Liquidity</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>News</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Score</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker}>
              <td style={{ padding: '6px 4px' }}><Link href={`/app/ticker-state/${row.ticker}`}>{row.ticker}</Link></td>
              <td style={{ padding: '6px 4px' }}>
                <div>{row.sector ?? '—'}</div>
                <div style={{ color: '#666', fontSize: 12 }}>{row.industry_name ?? '—'}</div>
                <div style={{ color: '#888', fontSize: 11 }}>
                  ICB {row.icb_code ?? '—'} • Industry {row.industry_code ?? '—'}
                </div>
              </td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.price_last ?? '—'}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.ret_1d)}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(row.ret_5d)}</td>
              <td style={{ padding: '6px 4px' }}>{row.trend_state} / {row.momentum_state}</td>
              <td style={{ padding: '6px 4px' }}>{row.liquidity_bucket}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.article_count_24h}</td>
              <td style={{ padding: '6px 4px', textAlign: 'right' }}>{row.watchlist_score.toFixed(2)}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={9} style={{ padding: '8px 4px', color: '#666' }}>No watchlist rows available.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
