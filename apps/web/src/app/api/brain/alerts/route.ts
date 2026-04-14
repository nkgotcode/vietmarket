import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const policy = await pool.query(`SELECT ticker, overall_result, blocking_flag, created_at FROM policy_results ORDER BY created_at DESC, ticker ASC LIMIT 50`);
  const health = await pool.query(`SELECT snapshot_id, overall_status, freshness_status, created_at FROM system_health_snapshots ORDER BY created_at DESC LIMIT 1`);
  const rows = [
    ...policy.rows.map((r) => ({ severity: r.blocking_flag ? 'warning' : 'info', message: `${r.ticker} policy=${r.overall_result}`, created_at: r.created_at })),
  ];
  return NextResponse.json({ ok: true, health: health.rows[0] ?? null, rows });
}
