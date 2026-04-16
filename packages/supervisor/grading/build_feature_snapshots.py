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
    CONFIG,
    VERSION,
    ensure_grade_version,
    latest_cycle_context,
    load_ticker_snapshot_inputs,
    replace_feature_rows,
)


def build_feature_snapshots() -> dict:
    with connect() as conn:
        ctx = latest_cycle_context(conn)
        ensure_grade_version(conn)
        raw_rows = load_ticker_snapshot_inputs(conn, ctx.cycle_id)
        critical_fields = CONFIG['feature_snapshot']['critical_fields']
        payload = []
        preview: list[dict[str, object]] = []
        now = utc_now()

        for row in raw_rows:
            missing_critical = [name for name in critical_fields if row.get(name) is None]
            financial_recency_days = row.get('financial_recency_days')
            stale_financials = bool(financial_recency_days is None or float(financial_recency_days) > 180)
            feature_json = {
                'price_last': row.get('price_last'),
                'volume_last': row.get('volume_last'),
                'turnover_last': row.get('turnover_last'),
                'ret_1d': row.get('ret_1d'),
                'ret_5d': row.get('ret_5d'),
                'ret_20d': row.get('ret_20d'),
                'volatility_20d': row.get('volatility_20d'),
                'financial_recency_days': financial_recency_days,
                'liquidity_bucket': row.get('liquidity_bucket'),
                'trend_state': row.get('trend_state'),
                'momentum_state': row.get('momentum_state'),
                'watchlist_score': row.get('watchlist_score'),
                'health_status': row.get('health_status'),
                'corporate_action_flag': row.get('corporate_action_flag'),
                'sector': row.get('sector'),
            }
            feature_quality_json = {
                'critical_fields': critical_fields,
                'missing_critical_features': missing_critical,
                'missing_feature_rate': round(len(missing_critical) / max(len(critical_fields), 1), 6),
                'stale_financials': stale_financials,
                'source_health': row.get('health_status') or 'unknown',
                'regime_confidence': round(ctx.regime_confidence, 6),
            }
            payload.append((
                ctx.cycle_id,
                row['ticker'],
                VERSION,
                ctx.market_regime,
                round(ctx.regime_confidence, 6),
                json.dumps(feature_json, default=str),
                json.dumps(feature_quality_json, default=str),
                now,
            ))
            if len(preview) < 10:
                preview.append({
                    'ticker': row['ticker'],
                    'liquidity_bucket': row.get('liquidity_bucket'),
                    'missing_critical_features': missing_critical,
                    'stale_financials': stale_financials,
                })

        replace_feature_rows(conn, ctx.cycle_id, payload)

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
        result = build_feature_snapshots()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_feature_snapshots',
            dataset_name='feature_snapshots',
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
            job_name='supervisor_build_feature_snapshots',
            dataset_name='feature_snapshots',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_feature_snapshots',
            stage='build_feature_snapshots',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
