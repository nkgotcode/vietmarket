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
from packages.supervisor.grading.common import VERSION, latest_cycle_context


def calibrate_grades() -> dict:
    with connect() as conn:
        ctx = latest_cycle_context(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                  count(*)::int,
                  avg(edge_estimate),
                  avg(downside_estimate),
                  avg(execution_cost_estimate),
                  avg(data_reliability_estimate),
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY edge_estimate),
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY execution_cost_estimate)
                FROM estimate_snapshots
                WHERE cycle_id = %s AND grade_version = %s
                ''',
                (ctx.cycle_id, VERSION),
            )
            row = cur.fetchone()

        if not row or int(row[0] or 0) == 0:
            raise RuntimeError('no_estimate_snapshots_for_latest_cycle')

    return {
        'ok': True,
        'cycle_id': ctx.cycle_id,
        'grade_version': VERSION,
        'row_count': int(row[0] or 0),
        'summary': {
            'avg_edge_estimate': float(row[1] or 0.0),
            'avg_downside_estimate': float(row[2] or 0.0),
            'avg_execution_cost_estimate': float(row[3] or 0.0),
            'avg_data_reliability_estimate': float(row[4] or 0.0),
            'median_edge_estimate': float(row[5] or 0.0),
            'median_execution_cost_estimate': float(row[6] or 0.0),
        },
        'notes': {
            'source_table': 'estimate_snapshots',
            'purpose': 'grade-plane calibration preview before persistence of full calibration artifacts',
        },
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = calibrate_grades()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_calibrate_grades',
            dataset_name='grade_versions',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=0,
            rows_upserted=0,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_calibrate_grades',
            dataset_name='grade_versions',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_calibrate_grades',
            stage='calibrate_grades',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
