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
    return NextResponse.json({ ok: true, cycle: null, score_version: null, rows: [] });
  }

  const cycle = cycleResult.rows[0];
  const versionResult = await pool.query(
    `SELECT score_version, status, description, config_json, created_at
       FROM score_versions
      ORDER BY created_at DESC
      LIMIT 1`
  );
  const scoreVersion = versionResult.rows[0] ?? null;

  const rowsResult = await pool.query(
    `SELECT d.cycle_id, d.ticker, d.score_version, d.alpha_score, d.quality_score, d.risk_score,
            d.execution_score, d.decision_score, d.model_confidence, d.evidence_confidence,
            d.execution_confidence, d.recommended_state, d.paper_eligible, d.block_reason_json,
            d.score_json, d.created_at,
            t.exchange, t.sector, t.price_last, t.ret_1d, t.ret_5d, t.ret_20d,
            t.volatility_20d, t.watchlist_score, t.trend_state, t.momentum_state, t.liquidity_bucket,
            c.total_score AS legacy_total_score, c.total_confidence AS legacy_total_confidence,
            c.ranking_bucket AS legacy_ranking_bucket
       FROM decision_scores d
       JOIN ticker_snapshots t
         ON t.cycle_id = d.cycle_id AND t.ticker = d.ticker
       LEFT JOIN candidate_rankings c
         ON c.cycle_id = d.cycle_id AND c.ticker = d.ticker
      WHERE d.cycle_id = $1 AND d.score_version = $2
      ORDER BY d.paper_eligible DESC, d.decision_score DESC, d.ticker ASC
      LIMIT 100`,
    [cycle.cycle_id, scoreVersion?.score_version ?? '']
  );

  return NextResponse.json({ ok: true, cycle, score_version: scoreVersion, rows: rowsResult.rows });
}
