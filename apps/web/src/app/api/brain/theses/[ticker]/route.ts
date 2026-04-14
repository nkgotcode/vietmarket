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
  const thesisResult = await pool.query(
    `SELECT thesis_id, cycle_id, ticker, thesis_type, side, horizon, confidence, why_now,
            supporting_evidence, contradicting_evidence, invalidation, suggested_priority,
            notes, raw_output_json, normalized_json, created_at
       FROM theses
      WHERE cycle_id = $1 AND ticker = $2
      LIMIT 1`,
    [cycle.cycle_id, symbol]
  );
  if (thesisResult.rows.length === 0) {
    return NextResponse.json({ ok: false, error: 'thesis_not_found', ticker: symbol }, { status: 404 });
  }
  const recommendationResult = await pool.query(
    `SELECT recommendation_id, ticker, status, side, horizon, confidence, suggested_priority,
            summary, why_now, recommendation_json, created_at
       FROM recommendations
      WHERE cycle_id = $1 AND ticker = $2
      LIMIT 1`,
    [cycle.cycle_id, symbol]
  );
  return NextResponse.json({
    ok: true,
    cycle,
    thesis: thesisResult.rows[0],
    recommendation: recommendationResult.rows[0] ?? null,
  });
}
