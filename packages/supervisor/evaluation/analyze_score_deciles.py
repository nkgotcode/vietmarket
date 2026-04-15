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

SCORE_VERSION = 'legacy_phase3_v1'
HORIZONS = (5, 10, 20)


def analyze_score_deciles() -> dict:
    created_at = utc_now()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM calibration_buckets')
            cur.execute('DELETE FROM calibration_runs')
            calibration_run_id = f'calrun_{new_run_id()}'

            bucket_rows = []
            preview = []
            total_sample_size = 0
            top_bottom_spreads: dict[int, float | None] = {}

            for horizon_days in HORIZONS:
                cur.execute(
                    '''
                    WITH base AS (
                      SELECT o.ticker,
                             c.total_score,
                             c.total_confidence,
                             o.forward_return,
                             o.excess_return,
                             o.max_drawdown
                      FROM ticker_forward_outcomes o
                      JOIN candidate_rankings c ON c.cycle_id = o.cycle_id AND c.ticker = o.ticker
                      WHERE o.horizon_days = %s
                        AND o.forward_return IS NOT NULL
                    ), bucketed AS (
                      SELECT ticker,
                             total_score,
                             total_confidence,
                             forward_return,
                             excess_return,
                             max_drawdown,
                             ntile(10) OVER (ORDER BY total_score DESC, total_confidence DESC, ticker ASC) AS decile
                      FROM base
                    )
                    SELECT decile,
                           count(*)::int AS sample_size,
                           avg(forward_return)::float8 AS avg_forward_return,
                           percentile_cont(0.5) WITHIN GROUP (ORDER BY forward_return)::float8 AS median_forward_return,
                           avg(CASE WHEN forward_return > 0 THEN 1.0 ELSE 0.0 END)::float8 AS positive_rate,
                           avg(excess_return)::float8 AS avg_excess_return,
                           avg(max_drawdown)::float8 AS avg_max_drawdown
                    FROM bucketed
                    GROUP BY decile
                    ORDER BY decile ASC
                    ''',
                    (horizon_days,),
                )
                rows = cur.fetchall()
                if not rows:
                    top_bottom_spreads[horizon_days] = None
                    continue
                top_avg = None
                bottom_avg = None
                for decile, sample_size, avg_forward_return, median_forward_return, positive_rate, avg_excess_return, avg_max_drawdown in rows:
                    bucket_name = f'score_decile_{decile}'
                    metric_json = {
                        'decile': int(decile),
                        'score_version': SCORE_VERSION,
                        'horizon_days': horizon_days,
                    }
                    bucket_rows.append(
                        (
                            calibration_run_id,
                            bucket_name,
                            horizon_days,
                            int(sample_size or 0),
                            avg_forward_return,
                            median_forward_return,
                            positive_rate,
                            avg_excess_return,
                            avg_max_drawdown,
                            json.dumps(metric_json, default=str),
                            created_at,
                        )
                    )
                    total_sample_size += int(sample_size or 0)
                    if int(decile) == 1:
                        top_avg = avg_forward_return
                    if int(decile) == 10:
                        bottom_avg = avg_forward_return
                    if len(preview) < 12:
                        preview.append(
                            {
                                'bucket_name': bucket_name,
                                'horizon_days': horizon_days,
                                'sample_size': int(sample_size or 0),
                                'avg_forward_return': avg_forward_return,
                                'positive_rate': positive_rate,
                            }
                        )
                top_bottom_spreads[horizon_days] = (top_avg - bottom_avg) if top_avg is not None and bottom_avg is not None else None

            summary = {
                'score_version': SCORE_VERSION,
                'bucket_row_count': len(bucket_rows),
                'total_sample_size': total_sample_size,
                'top_bottom_spreads': top_bottom_spreads,
            }
            cur.execute(
                'INSERT INTO calibration_runs (calibration_run_id, score_version, scope, summary_json, created_at) VALUES (%s,%s,%s,%s,%s)',
                (calibration_run_id, SCORE_VERSION, 'score_deciles', json.dumps(summary, default=str), created_at),
            )
            execute_values(
                cur,
                '''
                INSERT INTO calibration_buckets (
                  calibration_run_id, bucket_name, horizon_days, sample_size,
                  avg_forward_return, median_forward_return, positive_rate,
                  avg_excess_return, avg_max_drawdown, metric_json, created_at
                ) VALUES %s
                ''',
                bucket_rows,
            )

    return {
        'ok': True,
        'calibration_run_id': calibration_run_id,
        'score_version': SCORE_VERSION,
        'bucket_count': len(bucket_rows),
        'total_sample_size': total_sample_size,
        'top_bottom_spreads': top_bottom_spreads,
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = analyze_score_deciles()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_analyze_score_deciles',
            dataset_name='calibration_buckets',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('bucket_count', 0),
            rows_upserted=result.get('bucket_count', 0),
            summary_json=result,
        )
        print(json_dumps(result))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_analyze_score_deciles',
            dataset_name='calibration_buckets',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_analyze_score_deciles',
            stage='analyze_score_deciles',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
