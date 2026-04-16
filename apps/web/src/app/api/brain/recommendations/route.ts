import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

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
    `SELECT r.recommendation_id, r.cycle_id, r.thesis_id, r.ticker,
            COALESCE(ds.final_state, p.promotion_state, r.status) AS status,
            ds.analytical_state,
            ds.policy_blocked,
            r.side, r.horizon,
            COALESCE((r.recommendation_json->>'forecast_reliability')::double precision, r.confidence, 0) AS forecast_reliability,
            (r.recommendation_json->>'evidence_reliability')::double precision AS evidence_reliability,
            (r.recommendation_json->>'execution_reliability')::double precision AS execution_reliability,
            r.suggested_priority, r.summary, r.why_now, r.recommendation_json, r.created_at,
            t.sector,
            t.snapshot_json->>'industry_name' AS industry_name,
            t.snapshot_json->>'icb_code' AS icb_code,
            t.snapshot_json->>'industry_code' AS industry_code,
            s.score_version,
            p.paper_eligible,
            ds.state_json,
            r.recommendation_json->>'Opportunity Grade' AS opportunity_grade,
            r.recommendation_json->>'Evidence Grade' AS evidence_grade,
            r.recommendation_json->>'Tradability Grade' AS tradability_grade,
            r.recommendation_json->>'Risk Containment Grade' AS risk_containment_grade
       FROM recommendations r
       LEFT JOIN ticker_snapshots t ON t.cycle_id = r.cycle_id AND t.ticker = r.ticker
       LEFT JOIN recommendation_scorecards s ON s.recommendation_id = r.recommendation_id
       LEFT JOIN promotion_decisions p ON p.recommendation_id = r.recommendation_id
       LEFT JOIN decision_states_v2 ds ON ds.cycle_id = r.cycle_id AND ds.ticker = r.ticker
         AND ds.grade_version = (SELECT grade_version FROM grade_versions ORDER BY created_at DESC LIMIT 1)
      WHERE r.cycle_id = $1
      ORDER BY CASE COALESCE(ds.final_state, p.promotion_state, r.status)
        WHEN 'paper_eligible' THEN 0
        WHEN 'candidate' THEN 1
        WHEN 'watch' THEN 2
        WHEN 'research_only' THEN 3
        WHEN 'blocked' THEN 4
        ELSE 9 END ASC,
        COALESCE((r.recommendation_json->>'forecast_reliability')::double precision, r.confidence, 0) DESC,
        r.suggested_priority ASC,
        r.ticker ASC`,
    [cycle.cycle_id]
  );

  return NextResponse.json({
    ok: true,
    cycle,
    rows: result.rows.map((row) => ({
      ...row,
      forecast_reliability: toNumber(row.forecast_reliability),
      evidence_reliability: toNumber(row.evidence_reliability),
      execution_reliability: toNumber(row.execution_reliability),
      paper_eligible: Boolean(row.paper_eligible),
      policy_blocked: Boolean(row.policy_blocked),
    })),
  });
}
