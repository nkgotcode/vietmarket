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
  const result = await pool.query(
    `SELECT r.recommendation_id, r.cycle_id, r.thesis_id, r.ticker, r.status, r.side, r.horizon,
            r.confidence, r.suggested_priority, r.summary, r.why_now, r.supporting_evidence,
            r.contradicting_evidence, r.invalidation, r.recommendation_json, r.created_at,
            t.sector,
            t.snapshot_json->>'industry_name' AS industry_name,
            t.snapshot_json->>'icb_code' AS icb_code,
            t.snapshot_json->>'industry_code' AS industry_code,
            s.score_version, s.alpha_score, s.quality_score, s.risk_score, s.execution_score,
            s.decision_score, s.model_confidence, s.evidence_confidence, s.execution_confidence,
            p.promotion_state AS recommended_state, p.paper_eligible, p.decision_json
       FROM recommendations r
       LEFT JOIN ticker_snapshots t ON t.cycle_id = r.cycle_id AND t.ticker = r.ticker
       LEFT JOIN recommendation_scorecards s ON s.recommendation_id = r.recommendation_id
       LEFT JOIN promotion_decisions p ON p.recommendation_id = r.recommendation_id
      WHERE r.cycle_id = $1
      ORDER BY CASE coalesce(p.promotion_state, r.status)
        WHEN 'paper_eligible' THEN 0
        WHEN 'candidate' THEN 1
        WHEN 'watch' THEN 2
        WHEN 'research_only' THEN 3
        WHEN 'blocked' THEN 4
        ELSE 9 END ASC,
        COALESCE(s.decision_score, 0) DESC,
        r.suggested_priority ASC,
        r.confidence DESC,
        r.ticker ASC`,
    [cycle.cycle_id]
  );
  return NextResponse.json({ ok: true, cycle, rows: result.rows });
}
