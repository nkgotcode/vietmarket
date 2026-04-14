type Snapshot = {
  ticker: string;
  exchange: string | null;
  sector: string | null;
  industry_name: string | null;
  icb_code: string | null;
  industry_code: string | null;
  classification_source?: string | null;
  price_last: number | null;
  volume_last: number | null;
  turnover_last: number | null;
  ret_1d: number | null;
  ret_5d: number | null;
  ret_20d: number | null;
  sma20_gap: number | null;
  sma50_gap: number | null;
  ema20_gap: number | null;
  volatility_20d: number | null;
  article_count_24h: number;
  corporate_action_flag: boolean;
  financial_recency_days: number | null;
  liquidity_bucket: string;
  trend_state: string;
  momentum_state: string;
  watchlist_score: number;
  health_status: string;
  snapshot_json?: Record<string, unknown> | null;
};

function pct(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

export default function TickerSnapshotCard({ snapshot }: { snapshot: Snapshot }) {
  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 12 }}>
      <div>
        <h2 style={{ margin: 0 }}>{snapshot.ticker}</h2>
        <div style={{ color: '#666' }}>{snapshot.exchange ?? '—'} • {snapshot.sector ?? '—'}</div>
        <div style={{ color: '#666', fontSize: 13 }}>{snapshot.industry_name ?? '—'}</div>
        <div style={{ color: '#888', fontSize: 12 }}>
          ICB {snapshot.icb_code ?? '—'} • Industry {snapshot.industry_code ?? '—'} • Source {snapshot.classification_source ?? '—'}
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
        <div><strong>Price</strong><div style={{ color: '#666' }}>{snapshot.price_last ?? '—'}</div></div>
        <div><strong>Volume</strong><div style={{ color: '#666' }}>{snapshot.volume_last ?? '—'}</div></div>
        <div><strong>Turnover</strong><div style={{ color: '#666' }}>{snapshot.turnover_last ?? '—'}</div></div>
        <div><strong>1D / 5D / 20D</strong><div style={{ color: '#666' }}>{pct(snapshot.ret_1d)} • {pct(snapshot.ret_5d)} • {pct(snapshot.ret_20d)}</div></div>
        <div><strong>SMA20 / SMA50 / EMA20 gap</strong><div style={{ color: '#666' }}>{pct(snapshot.sma20_gap)} • {pct(snapshot.sma50_gap)} • {pct(snapshot.ema20_gap)}</div></div>
        <div><strong>Volatility 20D</strong><div style={{ color: '#666' }}>{pct(snapshot.volatility_20d)}</div></div>
        <div><strong>Trend / momentum</strong><div style={{ color: '#666' }}>{snapshot.trend_state} / {snapshot.momentum_state}</div></div>
        <div><strong>Liquidity</strong><div style={{ color: '#666' }}>{snapshot.liquidity_bucket}</div></div>
        <div><strong>Health</strong><div style={{ color: '#666' }}>{snapshot.health_status}</div></div>
        <div><strong>Articles 24h</strong><div style={{ color: '#666' }}>{snapshot.article_count_24h}</div></div>
        <div><strong>Corporate action flag</strong><div style={{ color: '#666' }}>{snapshot.corporate_action_flag ? 'yes' : 'no'}</div></div>
        <div><strong>Financial recency (days)</strong><div style={{ color: '#666' }}>{snapshot.financial_recency_days ?? '—'}</div></div>
      </div>
      <div><strong>Watchlist score:</strong> {snapshot.watchlist_score.toFixed(2)}</div>
      {snapshot.snapshot_json ? (
        <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>
          {JSON.stringify(snapshot.snapshot_json, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}
