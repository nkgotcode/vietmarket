import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

function toNumber(value: unknown): number {
  return typeof value === 'number' ? value : Number(value ?? 0);
}

function isWritablePrimary(row: { transaction_read_only: unknown; in_recovery: unknown }) {
  return String(row.transaction_read_only ?? '').toLowerCase() !== 'on' && !Boolean(row.in_recovery);
}

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const cycleResult = await pool.query(
    `SELECT cycle_id, regime_code, overall_status, freshness_status, created_at
       FROM market_state_cycles
      ORDER BY created_at DESC
      LIMIT 1`
  );
  const cycle = cycleResult.rows[0] ?? null;

  const [dbResult, policyResult, gateRunResult, admissionSummaryResult, admissionsResult] = await Promise.all([
    pool.query(`SELECT current_database() AS database_name,
                       current_user AS current_user,
                       current_setting('transaction_read_only') AS transaction_read_only,
                       pg_is_in_recovery() AS in_recovery,
                       inet_server_addr()::text AS server_addr,
                       inet_server_port() AS server_port,
                       version() AS postgres_version,
                       now() AS observed_at`),
    pool.query(`SELECT promotion_policy_version, status, paper_trading_enabled, thresholds_json, notes_json, created_at
                  FROM promotion_policy_versions
                 ORDER BY CASE WHEN status = 'active' THEN 0 ELSE 1 END, created_at DESC
                 LIMIT 1`),
    pool.query(`SELECT run_id, status, rows_written, rows_upserted, started_at, finished_at, summary_json
                  FROM worker_runs
                 WHERE job_name = 'supervisor_evaluate_promotion_gate'
                 ORDER BY started_at DESC
                 LIMIT 1`),
    cycle
      ? pool.query(
          `SELECT admission_status, count(*)::int AS count
             FROM paper_trade_admissions
            WHERE cycle_id = $1
            GROUP BY admission_status
            ORDER BY admission_status ASC`,
          [cycle.cycle_id]
        )
      : Promise.resolve({ rows: [] }),
    cycle
      ? pool.query(
          `SELECT a.admission_status,
                  a.ticker,
                  a.score_version,
                  a.promotion_policy_version,
                  a.policy_result,
                  a.paper_trading_enabled,
                  a.admission_json,
                  a.created_at,
                  p.promotion_state,
                  p.paper_eligible,
                  s.decision_score,
                  s.model_confidence,
                  s.evidence_confidence,
                  s.execution_confidence
             FROM paper_trade_admissions a
             LEFT JOIN promotion_decisions p ON p.recommendation_id = a.recommendation_id
             LEFT JOIN recommendation_scorecards s ON s.recommendation_id = a.recommendation_id
            WHERE a.cycle_id = $1
            ORDER BY CASE a.admission_status
              WHEN 'admitted' THEN 0
              WHEN 'below_thresholds' THEN 1
              WHEN 'blocked_policy' THEN 2
              WHEN 'not_paper_eligible' THEN 3
              WHEN 'disabled' THEN 4
              ELSE 9 END ASC,
              COALESCE(s.decision_score, 0) DESC,
              a.ticker ASC
            LIMIT 50`,
          [cycle.cycle_id]
        )
      : Promise.resolve({ rows: [] }),
  ]);

  const db = dbResult.rows[0] ?? null;
  const admissionCounts = Object.fromEntries(
    admissionSummaryResult.rows.map((row) => [String(row.admission_status), Number(row.count)])
  );
  const admissionTotal = Object.values(admissionCounts).reduce((sum, value) => sum + Number(value), 0);

  return NextResponse.json({
    ok: true,
    cycle,
    db_target: db
      ? {
          ...db,
          server_port: toNumber(db.server_port),
          in_recovery: Boolean(db.in_recovery),
          writable_primary: isWritablePrimary(db),
        }
      : null,
    active_policy: policyResult.rows[0]
      ? {
          ...policyResult.rows[0],
          paper_trading_enabled: Boolean(policyResult.rows[0].paper_trading_enabled),
          thresholds_json: (policyResult.rows[0].thresholds_json ?? null) as JsonValue,
          notes_json: (policyResult.rows[0].notes_json ?? null) as JsonValue,
        }
      : null,
    latest_gate_run: gateRunResult.rows[0]
      ? {
          ...gateRunResult.rows[0],
          rows_written: toNumber(gateRunResult.rows[0].rows_written),
          rows_upserted: toNumber(gateRunResult.rows[0].rows_upserted),
          summary_json: (gateRunResult.rows[0].summary_json ?? null) as JsonValue,
        }
      : null,
    admissions: {
      counts: admissionCounts,
      total: admissionTotal,
      rows: admissionsResult.rows.map((row) => ({
        ...row,
        decision_score: toNumber(row.decision_score),
        model_confidence: toNumber(row.model_confidence),
        evidence_confidence: toNumber(row.evidence_confidence),
        execution_confidence: toNumber(row.execution_confidence),
        paper_eligible: Boolean(row.paper_eligible),
        paper_trading_enabled: Boolean(row.paper_trading_enabled),
        admission_json: (row.admission_json ?? null) as JsonValue,
      })),
    },
  });
}
