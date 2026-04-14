type PnlRow = { cycle_id: string; market_value: number; unrealized_pnl: number; realized_pnl: number; cash_balance: number; created_at: string };

export default function PnLChart({ rows }: { rows: PnlRow[] }) {
  return (
    <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>
      {JSON.stringify(rows, null, 2)}
    </pre>
  );
}
