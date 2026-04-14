#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.freshness_builder import build_freshness
from packages.supervisor.health.worker_run_writer import write_worker_run


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_freshness()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_freshness',
            dataset_name='control_plane',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('count', 0),
            rows_upserted=result.get('count', 0),
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_freshness',
            dataset_name='control_plane',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_freshness',
            stage='build_freshness',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise