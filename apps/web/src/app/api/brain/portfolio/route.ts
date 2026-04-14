import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const snapshot = await pool.query(`SELECT snapshot_id, cycle_id, cash_balance, gross_exposure, net_exposure, market_value, unrealized_pnl, realized_pnl, positions_count, snapshot_json, created_at FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1`);
  const positions = await pool.query(`SELECT ticker, qty, avg_cost, market_price, market_value, unrealized_pnl, realized_pnl, updated_at FROM positions ORDER BY market_value DESC NULLS LAST, ticker ASC`);
  return NextResponse.json({ ok: true, snapshot: snapshot.rows[0] ?? null, positions: positions.rows });
}
