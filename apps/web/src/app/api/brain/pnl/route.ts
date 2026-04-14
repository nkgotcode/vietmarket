import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const snapshot = await pool.query(`SELECT cycle_id, market_value, unrealized_pnl, realized_pnl, cash_balance, created_at FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 20`);
  return NextResponse.json({ ok: true, rows: snapshot.rows });
}
