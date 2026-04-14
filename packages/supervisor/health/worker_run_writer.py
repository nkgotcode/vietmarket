from __future__ import annotations

import json
from datetime import datetime

from packages.supervisor.common.db import connect


def write_worker_run(*, run_id: str, job_name: str, status: str, started_at: datetime,
                     finished_at: datetime | None = None, dataset_name: str | None = None,
                     nomad_job_id: str | None = None, nomad_alloc_id: str | None = None,
                     node_name: str | None = None, rows_read: int = 0, rows_written: int = 0,
                     rows_upserted: int = 0, warnings_count: int = 0, errors_count: int = 0,
                     summary_json: dict | None = None) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO worker_runs (
                  run_id, job_name, dataset_name, nomad_job_id, nomad_alloc_id, node_name,
                  started_at, finished_at, status, rows_read, rows_written, rows_upserted,
                  warnings_count, errors_count, summary_json
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id) DO UPDATE SET
                  finished_at = EXCLUDED.finished_at,
                  status = EXCLUDED.status,
                  rows_read = EXCLUDED.rows_read,
                  rows_written = EXCLUDED.rows_written,
                  rows_upserted = EXCLUDED.rows_upserted,
                  warnings_count = EXCLUDED.warnings_count,
                  errors_count = EXCLUDED.errors_count,
                  summary_json = EXCLUDED.summary_json
                ''',
                (run_id, job_name, dataset_name, nomad_job_id, nomad_alloc_id, node_name,
                 started_at, finished_at, status, rows_read, rows_written, rows_upserted,
                 warnings_count, errors_count, json.dumps(summary_json or {}))
            )