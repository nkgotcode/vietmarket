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

  const [
    runResult,
    outcomesResult,
    portfolioResult,
    calibrationResult,
    replayRunResult,
    replayRowsResult,
    promptsResult,
    modelRunsResult,
    labelsCoverageResult,
    latestCalibrationRunResult,
    calibrationBucketsResult,
    cohortMetricsResult,
    gradeVersionsResult,
    gradePreviewResult,
  ] = await Promise.all([
    pool.query(`SELECT supervisor_run_id, mode, status, latest_health_status, latest_cycle_id, started_at, finished_at FROM supervisor_runs WHERE status = 'complete' ORDER BY started_at DESC LIMIT 1`),
    pool.query(`SELECT outcome_status, count(*)::int AS count FROM recommendation_outcomes GROUP BY outcome_status ORDER BY outcome_status ASC`),
    pool.query(`SELECT cycle_id, cash_balance, market_value, unrealized_pnl, realized_pnl, positions_count, created_at FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1`),
    pool.query(`SELECT metric_name, metric_value, metric_json, updated_at FROM calibration_metrics ORDER BY metric_name ASC`),
    pool.query(`SELECT replay_run_id, cycle_id, replay_scope, summary_json, created_at FROM replay_runs ORDER BY created_at DESC LIMIT 1`),
    pool.query(`SELECT rr.replay_run_id, rr.ticker, rr.result_json, rr.created_at FROM replay_results rr WHERE rr.replay_run_id = (SELECT replay_run_id FROM replay_runs ORDER BY created_at DESC LIMIT 1) ORDER BY ((rr.result_json->>'total_score')::double precision) DESC NULLS LAST, rr.ticker ASC LIMIT 20`),
    pool.query(`SELECT prompt_name, prompt_version, updated_at FROM prompt_versions ORDER BY prompt_name ASC`),
    pool.query(`SELECT model_run_id, cycle_id, run_kind, model_name, summary_json, created_at FROM model_runs ORDER BY created_at DESC LIMIT 20`),
    pool.query(`SELECT horizon_days, count(*)::int AS row_count, avg(forward_return)::float8 AS avg_forward_return, avg(excess_return)::float8 AS avg_excess_return FROM ticker_forward_outcomes GROUP BY horizon_days ORDER BY horizon_days ASC`),
    pool.query(`SELECT calibration_run_id, score_version, scope, summary_json, created_at FROM calibration_runs ORDER BY created_at DESC LIMIT 1`),
    pool.query(`SELECT bucket_name, horizon_days, sample_size, avg_forward_return, median_forward_return, positive_rate, avg_excess_return, avg_max_drawdown, metric_json, created_at FROM calibration_buckets WHERE calibration_run_id = (SELECT calibration_run_id FROM calibration_runs ORDER BY created_at DESC LIMIT 1) ORDER BY horizon_days ASC, bucket_name ASC`),
    pool.query(`SELECT cohort_type, cohort_key, horizon_days, sample_size, positive_rate, avg_forward_return, median_forward_return, avg_excess_return, avg_max_drawdown, summary_json, created_at FROM cohort_metrics ORDER BY created_at DESC, cohort_type ASC, horizon_days ASC, sample_size DESC LIMIT 60`),
    pool.query(`SELECT grade_version, status, description, created_at FROM grade_versions ORDER BY created_at DESC LIMIT 5`),
    pool.query(`SELECT ds.grade_version,
                       ds.ticker,
                       ds.analytical_state,
                       ds.final_state,
                       ds.paper_eligible,
                       ds.policy_blocked,
                       rs.forecast_reliability,
                       rs.evidence_reliability,
                       rs.execution_reliability,
                       o.grade_label AS opportunity_grade,
                       e.grade_label AS evidence_grade,
                       t.grade_label AS tradability_grade,
                       r.grade_label AS risk_containment_grade,
                       ds.created_at
                  FROM decision_states_v2 ds
                  JOIN reliability_snapshots rs ON rs.cycle_id = ds.cycle_id AND rs.ticker = ds.ticker AND rs.grade_version = ds.grade_version
                  JOIN opportunity_grades o ON o.cycle_id = ds.cycle_id AND o.ticker = ds.ticker AND o.grade_version = ds.grade_version
                  JOIN evidence_grades e ON e.cycle_id = ds.cycle_id AND e.ticker = ds.ticker AND e.grade_version = ds.grade_version
                  JOIN tradability_grades t ON t.cycle_id = ds.cycle_id AND t.ticker = ds.ticker AND t.grade_version = ds.grade_version
                  JOIN risk_containment_grades r ON r.cycle_id = ds.cycle_id AND r.ticker = ds.ticker AND r.grade_version = ds.grade_version
                 WHERE ds.cycle_id = (SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1)
                   AND ds.grade_version = (SELECT grade_version FROM grade_versions ORDER BY created_at DESC LIMIT 1)
                 ORDER BY ds.paper_eligible DESC, rs.forecast_reliability DESC, ds.ticker ASC
                 LIMIT 20`),
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
    labels_coverage: labelsCoverageResult.rows.map((row) => ({
      horizon_days: Number(row.horizon_days),
      row_count: Number(row.row_count),
      avg_forward_return: Number(row.avg_forward_return ?? 0),
      avg_excess_return: Number(row.avg_excess_return ?? 0),
    })),
    calibration_run: latestCalibrationRunResult.rows[0] ?? null,
    calibration_buckets: calibrationBucketsResult.rows.map((row) => ({
      bucket_name: row.bucket_name,
      horizon_days: Number(row.horizon_days),
      sample_size: Number(row.sample_size),
      avg_forward_return: Number(row.avg_forward_return ?? 0),
      median_forward_return: Number(row.median_forward_return ?? 0),
      positive_rate: Number(row.positive_rate ?? 0),
      avg_excess_return: Number(row.avg_excess_return ?? 0),
      avg_max_drawdown: Number(row.avg_max_drawdown ?? 0),
      metric_json: row.metric_json as JsonValue,
      created_at: row.created_at,
    })),
    cohort_metrics: cohortMetricsResult.rows.map((row) => ({
      cohort_type: row.cohort_type,
      cohort_key: row.cohort_key,
      horizon_days: Number(row.horizon_days),
      sample_size: Number(row.sample_size),
      positive_rate: Number(row.positive_rate ?? 0),
      avg_forward_return: Number(row.avg_forward_return ?? 0),
      median_forward_return: Number(row.median_forward_return ?? 0),
      avg_excess_return: Number(row.avg_excess_return ?? 0),
      avg_max_drawdown: Number(row.avg_max_drawdown ?? 0),
      summary_json: row.summary_json as JsonValue,
      created_at: row.created_at,
    })),
    grade_versions: gradeVersionsResult.rows,
    grade_preview: gradePreviewResult.rows.map((row) => ({
      ...row,
      forecast_reliability: Number(row.forecast_reliability ?? 0),
      evidence_reliability: Number(row.evidence_reliability ?? 0),
      execution_reliability: Number(row.execution_reliability ?? 0),
      paper_eligible: Boolean(row.paper_eligible),
      policy_blocked: Boolean(row.policy_blocked),
    })),
  });
}
