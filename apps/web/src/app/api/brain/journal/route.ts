import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const result = await pool.query(`SELECT decision_id, cycle_id, ticker, decision_type, status, created_at FROM supervisor_decisions ORDER BY created_at DESC LIMIT 200`);
  return NextResponse.json({ ok: true, rows: result.rows });
}
