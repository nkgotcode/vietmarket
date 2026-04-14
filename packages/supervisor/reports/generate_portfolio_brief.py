#!/usr/bin/env python3
from __future__ import annotations

import json

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_brief_id, new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.snapshots.common import to_jsonable


def generate_portfolio_brief() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT cycle_id, cash_balance, market_value, unrealized_pnl, realized_pnl, positions_count, snapshot_json FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1')
            row = cur.fetchone()
            if not row:
                raise RuntimeError('no_portfolio_snapshot')
            cycle_id, cash_balance, market_value, unrealized_pnl, realized_pnl, positions_count, snapshot_json = row
            title = 'Portfolio brief'
            summary_text = f'Portfolio snapshot with {positions_count} positions, market value {float(market_value or 0.0):.2f}, unrealized PnL {float(unrealized_pnl or 0.0):.2f}.'
            brief_json = {'cash_balance': cash_balance, 'market_value': market_value, 'unrealized_pnl': unrealized_pnl, 'realized_pnl': realized_pnl, 'positions_count': positions_count, 'snapshot_json': snapshot_json}
            cur.execute('DELETE FROM daily_briefs WHERE cycle_id = %s AND brief_type = %s', (cycle_id, 'portfolio'))
            cur.execute('INSERT INTO daily_briefs (brief_id, cycle_id, brief_type, title, summary_text, brief_json, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)', (new_brief_id(), cycle_id, 'portfolio', title, summary_text, json.dumps(to_jsonable(brief_json), default=str), utc_now()))
        return {'ok': True, 'cycle_id': cycle_id, 'brief_type': 'portfolio', 'positions_count': positions_count}


if __name__ == '__main__':
    run_id = new_run_id(); started_at = utc_now()
    try:
        result = generate_portfolio_brief(); finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_generate_portfolio_brief', dataset_name='portfolio_brief', status='complete', started_at=started_at, finished_at=finished_at, rows_written=1, rows_upserted=1, summary_json=result)
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_generate_portfolio_brief', dataset_name='portfolio_brief', status='failed', started_at=started_at, finished_at=finished_at, errors_count=1, summary_json={'error': str(exc)})
        write_failure(failure_id=new_failure_id(), run_id=run_id, job_name='supervisor_generate_portfolio_brief', stage='generate_portfolio_brief', error_class=type(exc).__name__, error_message=str(exc), retryable=False)
        raise
