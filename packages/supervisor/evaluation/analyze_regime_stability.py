#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.evaluation.common import execute_values, json_dumps
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run

HORIZONS = (5, 10, 20)


def analyze_regime_stability() -> dict:
    created_at = utc_now()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cohort_metrics WHERE cohort_type IN ('market_regime', 'liquidity_bucket')")
            payload = []
            preview = []
            for cohort_type, column_name in (('market_regime', 'market_regime'), ('liquidity_bucket', 'liquidity_bucket')):
                for horizon_days in HORIZONS:
                    cur.execute(
                        f'''
                        SELECT COALESCE({column_name}, 'unknown') AS cohort_key,
                               count(*)::int AS sample_size,
                               avg(CASE WHEN forward_return > 0 THEN 1.0 ELSE 0.0 END)::float8 AS positive_rate,
                               avg(forward_return)::float8 AS avg_forward_return,
                               percentile_cont(0.5) WITHIN GROUP (ORDER BY forward_return)::float8 AS median_forward_return,
                               avg(excess_return)::float8 AS avg_excess_return,
                               avg(max_drawdown)::float8 AS avg_max_drawdown
                        FROM ticker_forward_outcomes
                        WHERE horizon_days = %s
                          AND forward_return IS NOT NULL
                        GROUP BY COALESCE({column_name}, 'unknown')
                        ORDER BY sample_size DESC, cohort_key ASC
                        ''',
                        (horizon_days,),
                    )
                    for cohort_key, sample_size, positive_rate, avg_forward_return, median_forward_return, avg_excess_return, avg_max_drawdown in cur.fetchall():
                        summary_json = {
                            'cohort_type': cohort_type,
                            'cohort_key': cohort_key,
                            'horizon_days': horizon_days,
                        }
                        payload.append(
                            (
                                f'cohort_{new_run_id()}',
                                cohort_type,
                                str(cohort_key),
                                horizon_days,
                                int(sample_size or 0),
                                positive_rate,
                                avg_forward_return,
                                median_forward_return,
                                avg_excess_return,
                                avg_max_drawdown,
                                json.dumps(summary_json, default=str),
                                created_at,
                            )
                        )
                        if len(preview) < 12:
                            preview.append(
                                {
                                    'cohort_type': cohort_type,
                                    'cohort_key': str(cohort_key),
                                    'horizon_days': horizon_days,
                                    'sample_size': int(sample_size or 0),
                                    'positive_rate': positive_rate,
                                    'avg_forward_return': avg_forward_return,
                                }
                            )
            execute_values(
                cur,
                '''
                INSERT INTO cohort_metrics (
                  cohort_metric_id, cohort_type, cohort_key, horizon_days, sample_size,
                  positive_rate, avg_forward_return, median_forward_return,
                  avg_excess_return, avg_max_drawdown, summary_json, created_at
                ) VALUES %s
                ''',
                payload,
            )
    return {
        'ok': True,
        'cohort_metric_count': len(payload),
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = analyze_regime_stability()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_analyze_regime_stability',
            dataset_name='cohort_metrics',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('cohort_metric_count', 0),
            rows_upserted=result.get('cohort_metric_count', 0),
            summary_json=result,
        )
        print(json_dumps(result))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_analyze_regime_stability',
            dataset_name='cohort_metrics',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_analyze_regime_stability',
            stage='analyze_regime_stability',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
