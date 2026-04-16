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
from packages.supervisor.grading.common import (
    VERSION,
    clamp,
    ensure_grade_version,
    latest_cycle_context,
    replace_estimate_rows,
)


def build_estimates() -> dict:
    with connect() as conn:
        ctx = latest_cycle_context(conn)
        ensure_grade_version(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT ticker, feature_json, feature_quality_json
                FROM feature_snapshots
                WHERE cycle_id = %s AND grade_version = %s
                ORDER BY ticker ASC
                ''',
                (ctx.cycle_id, VERSION),
            )
            rows = cur.fetchall()

        if not rows:
            raise RuntimeError('no_feature_snapshots_for_latest_cycle')

        payload = []
        preview: list[dict[str, object]] = []
        now = utc_now()
        regime_bonus = 0.06 if ctx.market_regime in {'momentum_expansion', 'risk_on'} else 0.0
        regime_penalty = 0.04 if ctx.market_regime in {'risk_off'} else 0.0

        for ticker, feature_json, feature_quality_json in rows:
            features = dict(feature_json or {})
            quality = dict(feature_quality_json or {})

            watchlist_score = float(features.get('watchlist_score') or 0.0)
            ret_5d = float(features.get('ret_5d') or 0.0)
            ret_20d = float(features.get('ret_20d') or 0.0)
            trend_state = str(features.get('trend_state') or 'unknown')
            momentum_state = str(features.get('momentum_state') or 'unknown')
            volatility = float(features.get('volatility_20d') or 0.0)
            turnover = float(features.get('turnover_last') or 0.0)
            volume = float(features.get('volume_last') or 0.0)
            liquidity_bucket = str(features.get('liquidity_bucket') or 'unknown')
            corporate_action = bool(features.get('corporate_action_flag'))
            missing_feature_rate = float(quality.get('missing_feature_rate') or 0.0)
            stale_financials = bool(quality.get('stale_financials'))
            source_health = str(quality.get('source_health') or 'unknown')

            edge_estimate = clamp(
                0.22 * clamp((ret_5d + 0.15) / 0.30)
                + 0.20 * clamp((ret_20d + 0.30) / 0.60)
                + 0.20 * clamp(watchlist_score / 100.0)
                + 0.19 * (1.0 if trend_state in {'up', 'bullish', 'strong'} else 0.55 if trend_state not in {'unknown', 'down', 'bearish'} else 0.25)
                + 0.19 * (1.0 if momentum_state in {'up', 'bullish', 'strong'} else 0.55 if momentum_state not in {'unknown', 'down', 'bearish'} else 0.25)
                + regime_bonus
                - regime_penalty
            )

            downside_estimate = clamp(
                0.50 * clamp(volatility / 0.18)
                + 0.20 * (1.0 if source_health == 'blocked' else 0.65 if source_health == 'degraded' else 0.20)
                + 0.15 * (1.0 if corporate_action else 0.10)
                + 0.15 * (1.0 if liquidity_bucket == 'low' else 0.85 if liquidity_bucket == 'unknown' else 0.30)
            )

            execution_cost_estimate = clamp(
                1.0 - (
                    0.45 * clamp(turnover / 150_000_000.0)
                    + 0.35 * clamp(volume / 3_000_000.0)
                    + 0.20 * (1.0 if liquidity_bucket == 'high' else 0.75 if liquidity_bucket == 'medium' else 0.45 if liquidity_bucket == 'low' else 0.15)
                )
            )

            data_reliability_estimate = clamp(
                0.55 * (1.0 - missing_feature_rate)
                + 0.20 * (0.35 if stale_financials else 1.0)
                + 0.15 * (0.30 if source_health == 'blocked' else 0.55 if source_health == 'degraded' else 1.0)
                + 0.10 * clamp(ctx.regime_confidence)
            )

            estimate_json = {
                'trend_state': trend_state,
                'momentum_state': momentum_state,
                'liquidity_bucket': liquidity_bucket,
                'missing_feature_rate': missing_feature_rate,
                'source_health': source_health,
                'corporate_action_flag': corporate_action,
                'regime': ctx.market_regime,
                'regime_confidence': round(ctx.regime_confidence, 6),
            }
            payload.append((
                ctx.cycle_id,
                ticker,
                VERSION,
                round(edge_estimate, 6),
                round(downside_estimate, 6),
                round(execution_cost_estimate, 6),
                round(data_reliability_estimate, 6),
                json.dumps(estimate_json, default=str),
                now,
            ))
            if len(preview) < 10:
                preview.append({
                    'ticker': ticker,
                    'edge_estimate': round(edge_estimate, 6),
                    'downside_estimate': round(downside_estimate, 6),
                    'execution_cost_estimate': round(execution_cost_estimate, 6),
                    'data_reliability_estimate': round(data_reliability_estimate, 6),
                })

        replace_estimate_rows(conn, ctx.cycle_id, payload)

    return {
        'ok': True,
        'cycle_id': ctx.cycle_id,
        'grade_version': VERSION,
        'row_count': len(payload),
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_estimates()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_estimates',
            dataset_name='estimate_snapshots',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result['row_count'],
            rows_upserted=result['row_count'],
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_estimates',
            dataset_name='estimate_snapshots',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_estimates',
            stage='build_estimates',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
