import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const result = await pool.query(
    `SELECT dataset_name, ticker, tf, max_event_ts, max_ingested_at, freshness_seconds, freshness_status, freshness_context_json, updated_at
       FROM dataset_freshness
      ORDER BY dataset_name ASC, tf ASC NULLS FIRST`
  );

  return NextResponse.json({ ok: true, rows: result.rows });
}