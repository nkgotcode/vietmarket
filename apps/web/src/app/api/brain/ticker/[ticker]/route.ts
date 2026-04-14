import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request, context: { params: Promise<{ ticker: string }> }) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const { ticker } = await context.params;
  const symbol = ticker.toUpperCase();
  const pool = getPgPool();
  const cycleResult = await pool.query(
    `SELECT cycle_id, overall_status, freshness_status, frontier_status, universe_count, regime_code, notes_json, created_at
       FROM market_state_cycles
      ORDER BY created_at DESC
      LIMIT 1`
  );

  if (cycleResult.rows.length === 0) {
    return NextResponse.json({ ok: false, error: 'no_market_state_cycle' }, { status: 404 });
  }

  const cycle = cycleResult.rows[0];
  const snapshotResult = await pool.query(
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
      WHERE cycle_id = $1 AND ticker = $2
      LIMIT 1`,
    [cycle.cycle_id, symbol]
  );

  if (snapshotResult.rows.length === 0) {
    return NextResponse.json({ ok: false, error: 'ticker_not_found', ticker: symbol }, { status: 404 });
  }

  const snapshot = snapshotResult.rows[0];
  const regimeResult = await pool.query(
    `SELECT cycle_id, market_regime, breadth_state, trend_state, liquidity_state, event_pressure_state, confidence, watchlist_count, reasoning_json, created_at
       FROM market_regime_snapshots
      WHERE cycle_id = $1
      LIMIT 1`,
    [cycle.cycle_id]
  );
  const sectorResult = await pool.query(
    `SELECT cycle_id, sector, names_count, adv_count, dec_count, breadth_pct, avg_ret_1d, avg_ret_5d, leadership_json, laggards_json, snapshot_json, created_at
       FROM sector_snapshots
      WHERE cycle_id = $1 AND sector = $2
      LIMIT 1`,
    [cycle.cycle_id, snapshot.sector]
  );

  return NextResponse.json({
    ok: true,
    cycle,
    snapshot,
    regime: regimeResult.rows[0] ?? null,
    sector: sectorResult.rows[0] ?? null,
  });
}
