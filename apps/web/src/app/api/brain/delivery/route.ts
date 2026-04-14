import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();
  const result = await pool.query(`SELECT delivery_id, delivery_kind, channel, delivery_status, target_ref, payload_json, response_json, created_at FROM delivery_events ORDER BY created_at DESC LIMIT 200`);
  return NextResponse.json({ ok: true, rows: result.rows });
}
