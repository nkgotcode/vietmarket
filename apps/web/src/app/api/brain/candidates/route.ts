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
  const rowsResult = await pool.query(
    `SELECT c.cycle_id, c.ticker, c.total_score, c.total_confidence, c.ranking_bucket,
            c.blocking_flag, c.ranking_reason_json, c.created_at,
            t.exchange, t.sector, t.price_last, t.ret_1d, t.ret_5d, t.ret_20d,
            t.watchlist_score, t.trend_state, t.momentum_state, t.liquidity_bucket,
            t.snapshot_json->>'industry_name' AS industry_name,
            t.snapshot_json->>'icb_code' AS icb_code,
            t.snapshot_json->>'industry_code' AS industry_code,
            t.snapshot_json->>'classification_source' AS classification_source
       FROM candidate_rankings c
       JOIN ticker_snapshots t
         ON t.cycle_id = c.cycle_id AND t.ticker = c.ticker
      WHERE c.cycle_id = $1
      ORDER BY c.blocking_flag ASC, c.total_score DESC, c.total_confidence DESC, c.ticker ASC
      LIMIT 100`,
    [cycle.cycle_id]
  );

  return NextResponse.json({ ok: true, cycle, rows: rowsResult.rows });
}
