#!/usr/bin/env python3
from __future__ import annotations

import json
from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_brief_id, new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.execution.approval_gate import evaluate_approval_requirements
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run


def stage_orders() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM broker_order_audit')
            cur.execute('DELETE FROM execution_approvals')
            cur.execute('DELETE FROM broker_order_staging')
            cur.execute("SELECT recommendation_id, ticker, side FROM recommendations WHERE status = 'active' ORDER BY suggested_priority ASC, confidence DESC, ticker ASC LIMIT 5")
            recs = cur.fetchall()
            preview = []
            for recommendation_id, ticker, side in recs:
                cur.execute('SELECT paper_order_id, qty, limit_price FROM paper_orders WHERE ticker = %s ORDER BY submitted_at DESC LIMIT 1', (ticker,))
                row = cur.fetchone()
                if not row:
                    continue
                paper_order_id, qty, limit_price = row
                staging_id = f'stage_{new_brief_id()}'
                approval = evaluate_approval_requirements(recommendation_id=recommendation_id, paper_order_id=paper_order_id)
                cur.execute('INSERT INTO broker_order_staging (staging_id, recommendation_id, paper_order_id, ticker, side, qty, stage_status, stage_json, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (staging_id, recommendation_id, paper_order_id, ticker, side, qty, 'pending_approval', json.dumps({'limit_price': limit_price, 'approval': approval}), utc_now()))
                cur.execute('INSERT INTO execution_approvals (approval_id, staging_id, approval_status, approver, approval_json, created_at) VALUES (%s,%s,%s,%s,%s,%s)', (f'appr_{new_brief_id()}', staging_id, 'required', None, json.dumps(approval), utc_now()))
                cur.execute('INSERT INTO broker_order_audit (audit_id, staging_id, audit_event, audit_json, created_at) VALUES (%s,%s,%s,%s,%s)', (f'audit_{new_brief_id()}', staging_id, 'staged_for_approval', json.dumps({'ticker': ticker, 'paper_order_id': paper_order_id}), utc_now()))
                preview.append({'ticker': ticker, 'staging_id': staging_id, 'allowed_for_staging': approval['allowed_for_staging']})
        return {'ok': True, 'staged_count': len(preview), 'preview': preview}

if __name__ == '__main__':
    run_id = new_run_id(); started_at = utc_now()
    try:
        result = stage_orders(); finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_stage_orders', dataset_name='execution_staging', status='complete', started_at=started_at, finished_at=finished_at, rows_written=result['staged_count'], rows_upserted=result['staged_count'], summary_json=result)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_stage_orders', dataset_name='execution_staging', status='failed', started_at=started_at, finished_at=finished_at, errors_count=1, summary_json={'error': str(exc)})
        write_failure(failure_id=f'fail_stage_{new_run_id()}', run_id=run_id, job_name='supervisor_stage_orders', stage='stage_orders', error_class=type(exc).__name__, error_message=str(exc), retryable=False)
        raise
