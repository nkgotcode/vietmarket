type Regime = {
  market_regime: string;
  breadth_state: string;
  trend_state: string;
  liquidity_state: string;
  event_pressure_state: string;
  confidence: number;
  watchlist_count: number;
  reasoning_json?: Record<string, unknown> | null;
};

export default function RegimeCard({ regime }: { regime: Regime | null }) {
  if (!regime) {
    return <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 16 }}>No regime snapshot available.</div>;
  }

  const tone = regime.market_regime === 'risk_off' ? '#8b0000' : regime.market_regime === 'momentum_expansion' ? '#0b6b2a' : '#304ffe';

  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 12 }}>
      <div>
        <div style={{ color: '#666', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>Current regime</div>
        <h2 style={{ margin: '6px 0 0', color: tone, textTransform: 'capitalize' }}>{regime.market_regime.replaceAll('_', ' ')}</h2>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
        <div><strong>Breadth</strong><div style={{ color: '#666' }}>{regime.breadth_state}</div></div>
        <div><strong>Trend</strong><div style={{ color: '#666' }}>{regime.trend_state}</div></div>
        <div><strong>Liquidity</strong><div style={{ color: '#666' }}>{regime.liquidity_state}</div></div>
        <div><strong>Event pressure</strong><div style={{ color: '#666' }}>{regime.event_pressure_state}</div></div>
        <div><strong>Confidence</strong><div style={{ color: '#666' }}>{regime.confidence}</div></div>
        <div><strong>Watchlist names</strong><div style={{ color: '#666' }}>{regime.watchlist_count}</div></div>
      </div>
      {regime.reasoning_json ? (
        <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>
          {JSON.stringify(regime.reasoning_json, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}
