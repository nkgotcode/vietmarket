import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const result = await pool.query(`SELECT cycle_id, ticker, recommendation_id, overall_result, blocking_flag, checks_json, summary_json, created_at FROM policy_results ORDER BY created_at DESC, ticker ASC LIMIT 100`);
  return NextResponse.json({ ok: true, rows: result.rows });
}
