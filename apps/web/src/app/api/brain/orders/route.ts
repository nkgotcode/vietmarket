import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const intents = await pool.query(`SELECT intent_id, cycle_id, recommendation_id, ticker, intent_status, side, target_qty, reference_price, notes_json, created_at FROM execution_intents ORDER BY created_at DESC, ticker ASC LIMIT 100`);
  const orders = await pool.query(`SELECT paper_order_id, intent_id, cycle_id, ticker, order_status, side, qty, limit_price, submitted_at, updated_at FROM paper_orders ORDER BY submitted_at DESC, ticker ASC LIMIT 100`);
  const fills = await pool.query(`SELECT paper_fill_id, paper_order_id, ticker, fill_qty, fill_price, filled_at, notes_json FROM paper_fills ORDER BY filled_at DESC, ticker ASC LIMIT 100`);
  return NextResponse.json({ ok: true, intents: intents.rows, orders: orders.rows, fills: fills.rows });
}
