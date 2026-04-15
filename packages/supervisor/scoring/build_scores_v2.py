#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.scoring.common import CONFIG, VERSION, clamp, clamp100, connect_rows, ensure_score_version, replace_v2_rows


def build_scores_v2() -> dict:
    with connect() as conn:
        cycle_id = _latest_cycle_id(conn)
        ensure_score_version(conn)
        ctx = connect_rows(conn, cycle_id)

        positive_rate = float(ctx.calibration.get('positive_rate_5d', 0.0))
        top_bottom_spread = float(ctx.calibration.get('top_bottom_spread_5d', 0.0))
        sample_size_5d = float(ctx.calibration.get('sample_size_5d', 0.0))
        calibration_strength = clamp((positive_rate - 0.45) / 0.20) * 0.55 + clamp(top_bottom_spread / 0.12) * 0.30 + clamp(sample_size_5d / 200.0) * 0.15

        alpha_rows = []
        quality_rows = []
        risk_rows = []
        execution_rows = []
        decision_rows = []
        preview = []
        now = utc_now()

        for row in ctx.rows:
            ticker = row['ticker']
            legacy_total = float(row.get('legacy_total_score') or 0.0)
            legacy_total_norm = legacy_total / 100.0
            alpha_raw = (
                float(row.get('trend_score') or 0.0) * CONFIG['alpha_weights']['trend'] +
                float(row.get('momentum_score') or 0.0) * CONFIG['alpha_weights']['momentum'] +
                float(row.get('catalyst_score') or 0.0) * CONFIG['alpha_weights']['catalyst'] +
                float(row.get('fundamentals_score') or 0.0) * CONFIG['alpha_weights']['fundamentals'] +
                legacy_total_norm * CONFIG['alpha_weights']['legacy_total_score']
            )
            alpha_score = clamp100(alpha_raw * 100.0)

            model_confidence = round(
                clamp(
                    0.50 * calibration_strength
                    + 0.20 * clamp(float(row.get('legacy_total_confidence') or 0.0))
                    + 0.15 * clamp(alpha_score / 100.0)
                    + 0.15 * clamp(ctx.regime_confidence)
                ),
                6,
            )

            recency_days = row.get('financial_recency_days')
            recency_score = 1.0
            if recency_days is None:
                recency_score = 0.30
            elif float(recency_days) > 365:
                recency_score = 0.45
            elif float(recency_days) > 180:
                recency_score = 0.70
            elif float(recency_days) > 120:
                recency_score = 0.82
            missing_penalty = 0.0
            for key in ('price_last', 'volume_last', 'turnover_last', 'volatility_20d'):
                if row.get(key) is None:
                    missing_penalty += 0.10
            quality_base = 0.35 * clamp(float(row.get('legacy_total_confidence') or 0.0)) + 0.25 * recency_score + 0.20 * (1.0 if row.get('health_status') == 'healthy' else 0.45) + 0.20 * (1.0 if row.get('liquidity_bucket') != 'unknown' else 0.35)
            evidence_confidence = round(clamp(quality_base - missing_penalty), 6)
            quality_score = clamp100(evidence_confidence * 100.0)

            volatility = float(row.get('volatility_20d') or 0.0)
            health_status = str(row.get('health_status') or 'unknown')
            corp_action = bool(row.get('corporate_action_flag'))
            liquidity_bucket = str(row.get('liquidity_bucket') or 'unknown')
            risk_raw = 100.0 - min(volatility * 240.0, 55.0)
            if health_status == 'degraded':
                risk_raw -= 18.0
            elif health_status == 'blocked':
                risk_raw -= 40.0
            if corp_action:
                risk_raw -= 7.5
            if liquidity_bucket == 'low':
                risk_raw -= 10.0
            elif liquidity_bucket == 'unknown':
                risk_raw -= 22.0
            risk_score = clamp100(risk_raw)
            block_flag = bool(row.get('legacy_blocking_flag')) or health_status == 'blocked' or volatility >= 0.18

            turnover = float(row.get('turnover_last') or 0.0)
            volume = float(row.get('volume_last') or 0.0)
            execution_raw = 45.0 * clamp(turnover / 150_000_000.0) + 35.0 * clamp(volume / 3_000_000.0) + 20.0 * (1.0 if liquidity_bucket == 'high' else 0.75 if liquidity_bucket == 'medium' else 0.45 if liquidity_bucket == 'low' else 0.15)
            execution_score = clamp100(execution_raw)
            execution_confidence = round(clamp(0.55 * clamp(execution_score / 100.0) + 0.45 * (1.0 if liquidity_bucket != 'unknown' else 0.25)), 6)

            weights = CONFIG['decision_weights']
            decision_score = clamp100(
                alpha_score * weights['alpha']
                + quality_score * weights['quality']
                + risk_score * weights['risk']
                + execution_score * weights['execution']
            )

            paper_thresholds = CONFIG['paper_thresholds']
            paper_eligible = (
                not block_flag
                and ctx.overall_status == 'healthy'
                and ctx.freshness_status == 'healthy'
                and decision_score >= paper_thresholds['decision_score']
                and model_confidence >= paper_thresholds['model_confidence']
                and evidence_confidence >= paper_thresholds['evidence_confidence']
                and execution_confidence >= paper_thresholds['execution_confidence']
                and risk_score >= paper_thresholds['risk_score']
                and execution_score >= paper_thresholds['execution_score']
            )

            if block_flag:
                recommended_state = 'blocked'
            elif paper_eligible:
                recommended_state = 'paper_eligible'
            elif decision_score >= 65.0 and model_confidence >= 0.55:
                recommended_state = 'candidate'
            elif decision_score >= 50.0:
                recommended_state = 'watch'
            else:
                recommended_state = 'research_only'

            alpha_reason = {
                'trend_score': float(row.get('trend_score') or 0.0),
                'momentum_score': float(row.get('momentum_score') or 0.0),
                'catalyst_score': float(row.get('catalyst_score') or 0.0),
                'fundamentals_score': float(row.get('fundamentals_score') or 0.0),
                'legacy_total_score': legacy_total,
                'calibration_strength': round(calibration_strength, 6),
            }
            quality_reason = {
                'legacy_total_confidence': float(row.get('legacy_total_confidence') or 0.0),
                'financial_recency_days': recency_days,
                'health_status': health_status,
                'liquidity_bucket': liquidity_bucket,
            }
            risk_reason = {
                'volatility_20d': volatility,
                'health_status': health_status,
                'corporate_action_flag': corp_action,
                'liquidity_bucket': liquidity_bucket,
                'legacy_blocking_flag': bool(row.get('legacy_blocking_flag')),
            }
            execution_reason = {
                'turnover_last': turnover,
                'volume_last': volume,
                'liquidity_bucket': liquidity_bucket,
            }
            block_reason = {
                'block_flag': block_flag,
                'overall_status': ctx.overall_status,
                'freshness_status': ctx.freshness_status,
                'legacy_bucket': row.get('legacy_bucket'),
            }
            score_json = {
                'market_regime': ctx.market_regime,
                'decision_weights': weights,
                'thresholds': paper_thresholds,
                'sector': row.get('sector'),
                'legacy_bucket': row.get('legacy_bucket'),
            }

            alpha_rows.append((ctx.cycle_id, ticker, VERSION, alpha_score, model_confidence, json.dumps(alpha_reason), now))
            quality_rows.append((ctx.cycle_id, ticker, VERSION, quality_score, evidence_confidence, json.dumps(quality_reason), now))
            risk_rows.append((ctx.cycle_id, ticker, VERSION, risk_score, block_flag, json.dumps(risk_reason), now))
            execution_rows.append((ctx.cycle_id, ticker, VERSION, execution_score, execution_confidence, json.dumps(execution_reason), now))
            decision_rows.append((ctx.cycle_id, ticker, VERSION, alpha_score, quality_score, risk_score, execution_score, decision_score, model_confidence, evidence_confidence, execution_confidence, recommended_state, paper_eligible, json.dumps(block_reason), json.dumps(score_json), now))

            if len(preview) < 12:
                preview.append({
                    'ticker': ticker,
                    'decision_score': decision_score,
                    'alpha_score': alpha_score,
                    'quality_score': quality_score,
                    'risk_score': risk_score,
                    'execution_score': execution_score,
                    'recommended_state': recommended_state,
                    'paper_eligible': paper_eligible,
                })

        replace_v2_rows(conn, ctx.cycle_id, alpha_rows, quality_rows, risk_rows, execution_rows, decision_rows)

    return {
        'ok': True,
        'cycle_id': ctx.cycle_id,
        'score_version': VERSION,
        'row_count': len(decision_rows),
        'paper_eligible_count': sum(1 for row in decision_rows if row[12]),
        'preview': preview,
    }


def _latest_cycle_id(conn) -> str:
    with conn.cursor() as cur:
        cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
        row = cur.fetchone()
    if not row:
        raise RuntimeError('no_market_state_cycle')
    return row[0]


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_scores_v2()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_scores_v2',
            dataset_name='decision_scores',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('row_count', 0) * 5,
            rows_upserted=result.get('row_count', 0) * 5,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_scores_v2',
            dataset_name='decision_scores',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_scores_v2',
            stage='build_scores_v2',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
