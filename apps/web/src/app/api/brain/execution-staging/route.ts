import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const staging = await pool.query(`SELECT staging_id, recommendation_id, paper_order_id, ticker, side, qty, stage_status, stage_json, created_at FROM broker_order_staging ORDER BY created_at DESC LIMIT 100`);
  const audits = await pool.query(`SELECT audit_id, staging_id, audit_event, audit_json, created_at FROM broker_order_audit ORDER BY created_at DESC LIMIT 100`);
  return NextResponse.json({ ok: true, staging: staging.rows, audits: audits.rows });
}
