import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const result = await pool.query(
    `SELECT brief_id, cycle_id, brief_type, title, summary_text, brief_json, created_at
       FROM daily_briefs
      WHERE brief_type = 'daily'
      ORDER BY created_at DESC
      LIMIT 1`
  );

  return NextResponse.json({ ok: true, brief: result.rows[0] ?? null });
}
