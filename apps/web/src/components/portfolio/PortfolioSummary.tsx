type Snapshot = {
  cash_balance: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  positions_count: number;
} | null;

type Position = {
  ticker: string;
  qty: number;
  avg_cost: number;
  market_price: number | null;
  market_value: number | null;
  unrealized_pnl: number;
};

export default function PortfolioSummary({ snapshot, positions }: { snapshot: Snapshot; positions: Position[] }) {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
        <div>Cash: {snapshot?.cash_balance ?? '—'}</div>
        <div>Market value: {snapshot?.market_value ?? '—'}</div>
        <div>Unrealized PnL: {snapshot?.unrealized_pnl ?? '—'}</div>
        <div>Realized PnL: {snapshot?.realized_pnl ?? '—'}</div>
        <div>Positions: {snapshot?.positions_count ?? 0}</div>
      </div>
      <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead><tr><th style={{textAlign:'left',padding:'6px 4px',borderBottom:'1px solid #eee'}}>Ticker</th><th style={{textAlign:'right',padding:'6px 4px',borderBottom:'1px solid #eee'}}>Qty</th><th style={{textAlign:'right',padding:'6px 4px',borderBottom:'1px solid #eee'}}>Avg cost</th><th style={{textAlign:'right',padding:'6px 4px',borderBottom:'1px solid #eee'}}>Market</th><th style={{textAlign:'right',padding:'6px 4px',borderBottom:'1px solid #eee'}}>UPnL</th></tr></thead>
          <tbody>
            {positions.map((p)=><tr key={p.ticker}><td style={{padding:'6px 4px'}}>{p.ticker}</td><td style={{padding:'6px 4px',textAlign:'right'}}>{p.qty}</td><td style={{padding:'6px 4px',textAlign:'right'}}>{p.avg_cost}</td><td style={{padding:'6px 4px',textAlign:'right'}}>{p.market_price ?? '—'}</td><td style={{padding:'6px 4px',textAlign:'right'}}>{p.unrealized_pnl}</td></tr>)}
            {positions.length===0 ? <tr><td colSpan={5} style={{padding:'8px 4px',color:'#666'}}>No positions.</td></tr> : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
