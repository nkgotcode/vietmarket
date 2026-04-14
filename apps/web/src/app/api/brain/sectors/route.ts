import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const cycleResult = await pool.query(
    `SELECT cycle_id, overall_status, freshness_status, frontier_status, universe_count, regime_code, notes_json, created_at
       FROM market_state_cycles
      ORDER BY created_at DESC
      LIMIT 1`
  );

  if (cycleResult.rows.length === 0) {
    return NextResponse.json({ ok: true, cycle: null, rows: [] });
  }

  const cycle = cycleResult.rows[0];
  const sectorsResult = await pool.query(
    `SELECT cycle_id, sector, names_count, adv_count, dec_count, breadth_pct, avg_ret_1d, avg_ret_5d, leadership_json, laggards_json, snapshot_json, created_at
       FROM sector_snapshots
      WHERE cycle_id = $1
      ORDER BY breadth_pct DESC NULLS LAST, avg_ret_5d DESC NULLS LAST, sector ASC`,
    [cycle.cycle_id]
  );

  return NextResponse.json({ ok: true, cycle, rows: sectorsResult.rows });
}
