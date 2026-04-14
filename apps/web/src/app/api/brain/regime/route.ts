import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const cycleResult = await pool.query(
    `SELECT cycle_id, source_health_snapshot_id, overall_status, freshness_status, frontier_status, universe_count, regime_code, notes_json, created_at
       FROM market_state_cycles
      ORDER BY created_at DESC
      LIMIT 1`
  );

  if (cycleResult.rows.length === 0) {
    return NextResponse.json({ ok: true, cycle: null, regime: null });
  }

  const cycle = cycleResult.rows[0];
  const regimeResult = await pool.query(
    `SELECT cycle_id, market_regime, breadth_state, trend_state, liquidity_state, event_pressure_state, confidence, watchlist_count, reasoning_json, created_at
       FROM market_regime_snapshots
      WHERE cycle_id = $1
      LIMIT 1`,
    [cycle.cycle_id]
  );

  return NextResponse.json({ ok: true, cycle, regime: regimeResult.rows[0] ?? null });
}
