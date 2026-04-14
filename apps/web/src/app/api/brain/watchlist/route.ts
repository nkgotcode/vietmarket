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
  const watchlistResult = await pool.query(
    `SELECT cycle_id, ticker, exchange, sector, price_last, volume_last, turnover_last,
            ret_1d, ret_5d, ret_20d, sma20_gap, sma50_gap, ema20_gap, volatility_20d,
            article_count_24h, corporate_action_flag, financial_recency_days,
            liquidity_bucket, trend_state, momentum_state, watchlist_score,
            health_status, snapshot_json,
            snapshot_json->>'industry_name' AS industry_name,
            snapshot_json->>'icb_code' AS icb_code,
            snapshot_json->>'industry_code' AS industry_code,
            snapshot_json->>'classification_source' AS classification_source,
            created_at
       FROM ticker_snapshots
      WHERE cycle_id = $1
      ORDER BY watchlist_score DESC, ret_5d DESC NULLS LAST, ticker ASC
      LIMIT 50`,
    [cycle.cycle_id]
  );

  return NextResponse.json({ ok: true, cycle, rows: watchlistResult.rows });
}
