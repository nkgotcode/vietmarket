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
    scoreVersionsResult,
    decisionScoresResult,
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
    pool.query(`SELECT score_version, status, description, config_json, created_at FROM score_versions ORDER BY created_at DESC LIMIT 5`),
    pool.query(`SELECT score_version, ticker, alpha_score, quality_score, risk_score, execution_score, decision_score, model_confidence, evidence_confidence, execution_confidence, recommended_state, paper_eligible, created_at FROM decision_scores WHERE cycle_id = (SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1) AND score_version = (SELECT score_version FROM score_versions ORDER BY created_at DESC LIMIT 1) ORDER BY paper_eligible DESC, decision_score DESC, ticker ASC LIMIT 20`),
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
    score_versions: scoreVersionsResult.rows,
    decision_scores_v2: decisionScoresResult.rows.map((row) => ({
      ...row,
      alpha_score: Number(row.alpha_score ?? 0),
      quality_score: Number(row.quality_score ?? 0),
      risk_score: Number(row.risk_score ?? 0),
      execution_score: Number(row.execution_score ?? 0),
      decision_score: Number(row.decision_score ?? 0),
      model_confidence: Number(row.model_confidence ?? 0),
      evidence_confidence: Number(row.evidence_confidence ?? 0),
      execution_confidence: Number(row.execution_confidence ?? 0),
      paper_eligible: Boolean(row.paper_eligible),
    })),
  });
}
