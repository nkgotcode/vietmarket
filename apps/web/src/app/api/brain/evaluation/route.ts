import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

function toNumber(value: unknown): number {
  return typeof value === 'number' ? value : Number(value ?? 0);
}

export async function GET(req: Request) {
  const denied = await requireAppAuth(req); if (denied) return denied;
  const pool = getPgPool();

  const [runResult, outcomesResult, portfolioResult, calibrationResult, replayRunResult, replayRowsResult, promptsResult, modelRunsResult] = await Promise.all([
    pool.query(`SELECT supervisor_run_id, mode, status, latest_health_status, latest_cycle_id, started_at, finished_at FROM supervisor_runs WHERE status = 'complete' ORDER BY started_at DESC LIMIT 1`),
    pool.query(`SELECT outcome_status, count(*)::int AS count FROM recommendation_outcomes GROUP BY outcome_status ORDER BY outcome_status ASC`),
    pool.query(`SELECT cycle_id, cash_balance, market_value, unrealized_pnl, realized_pnl, positions_count, created_at FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1`),
    pool.query(`SELECT metric_name, metric_value, metric_json, updated_at FROM calibration_metrics ORDER BY metric_name ASC`),
    pool.query(`SELECT replay_run_id, cycle_id, replay_scope, summary_json, created_at FROM replay_runs ORDER BY created_at DESC LIMIT 1`),
    pool.query(`SELECT rr.replay_run_id, rr.ticker, rr.result_json, rr.created_at FROM replay_results rr WHERE rr.replay_run_id = (SELECT replay_run_id FROM replay_runs ORDER BY created_at DESC LIMIT 1) ORDER BY ((rr.result_json->>'total_score')::double precision) DESC NULLS LAST, rr.ticker ASC LIMIT 20`),
    pool.query(`SELECT prompt_name, prompt_version, updated_at FROM prompt_versions ORDER BY prompt_name ASC`),
    pool.query(`SELECT model_run_id, cycle_id, run_kind, model_name, summary_json, created_at FROM model_runs ORDER BY created_at DESC LIMIT 20`),
  ]);

  const outcomeCounts = Object.fromEntries(outcomesResult.rows.map((row) => [String(row.outcome_status), Number(row.count)]));
  const totalOutcomes = Object.values(outcomeCounts).reduce((sum, value) => sum + Number(value), 0);
  const positiveRate = totalOutcomes > 0 ? Number(outcomeCounts.positive ?? 0) / totalOutcomes : 0;
  const portfolio = portfolioResult.rows[0] ?? null;
  const equity = portfolio ? toNumber(portfolio.cash_balance) + toNumber(portfolio.market_value) + toNumber(portfolio.realized_pnl) + toNumber(portfolio.unrealized_pnl) : 0;

  const calibration = calibrationResult.rows.map((row) => ({
    metric_name: row.metric_name,
    metric_value: Number(row.metric_value),
    metric_json: row.metric_json as JsonValue,
    updated_at: row.updated_at,
  }));

  return NextResponse.json({
    ok: true,
    latest_run: runResult.rows[0] ?? null,
    outcomes: {
      counts: outcomeCounts,
      total: totalOutcomes,
      positive_rate: positiveRate,
    },
    portfolio: portfolio ? { ...portfolio, equity } : null,
    calibration,
    replay: {
      run: replayRunResult.rows[0] ?? null,
      rows: replayRowsResult.rows,
    },
    prompts: promptsResult.rows,
    model_runs: modelRunsResult.rows,
  });
}
