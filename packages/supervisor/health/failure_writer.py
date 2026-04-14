from __future__ import annotations

import hashlib

from packages.supervisor.common.db import connect


def write_failure(*, failure_id: str, job_name: str, error_class: str, error_message: str,
                  run_id: str | None = None, stage: str | None = None, retryable: bool = False) -> None:
    error_hash = hashlib.sha256(f'{error_class}:{error_message}'.encode()).hexdigest()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO worker_failures (
                  failure_id, run_id, job_name, stage, error_class, error_hash, error_message, retryable
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (failure_id, run_id, job_name, stage, error_class, error_hash, error_message, retryable)
            )