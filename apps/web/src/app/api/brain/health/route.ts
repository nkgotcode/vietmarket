import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const snapshotResult = await pool.query(
    `SELECT snapshot_id, cycle_id, overall_status, data_plane_status, freshness_status, notes_json, created_at
       FROM system_health_snapshots
      ORDER BY created_at DESC
      LIMIT 1`
  );

  if (snapshotResult.rows.length === 0) {
    return NextResponse.json({ ok: true, snapshot: null, issues: [] });
  }

  const snapshot = snapshotResult.rows[0];
  const issueResult = await pool.query(
    `SELECT issue_id, severity, scope_type, scope_key, issue_code, issue_message, blocking, created_at
       FROM system_health_issues
      WHERE snapshot_id = $1
      ORDER BY blocking DESC, severity DESC, created_at DESC`,
    [snapshot.snapshot_id]
  );

  return NextResponse.json({ ok: true, snapshot, issues: issueResult.rows });
}