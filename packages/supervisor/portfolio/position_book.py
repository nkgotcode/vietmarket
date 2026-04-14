from __future__ import annotations

import json

from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.portfolio.pnl import compute_unrealized_pnl
from packages.supervisor.snapshots.common import to_jsonable


def rebuild_positions(conn, *, cycle_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM positions')
        cur.execute(
            '''
            SELECT f.ticker,
                   sum(CASE WHEN o.side = 'long' THEN f.fill_qty ELSE -f.fill_qty END) AS qty,
                   sum((CASE WHEN o.side = 'long' THEN f.fill_qty ELSE -f.fill_qty END) * f.fill_price) AS signed_notional
            FROM paper_fills f
            JOIN paper_orders o ON o.paper_order_id = f.paper_order_id
            GROUP BY f.ticker
            '''
        )
        rows = cur.fetchall()
        preview = []
        for ticker, qty, signed_notional in rows:
            qty = float(qty or 0.0)
            avg_cost = abs(float(signed_notional or 0.0) / qty) if qty else 0.0
            cur.execute(
                'SELECT price_last FROM ticker_snapshots WHERE cycle_id = %s AND ticker = %s LIMIT 1',
                (cycle_id, ticker),
            )
            row = cur.fetchone()
            market_price = float(row[0]) if row and row[0] is not None else None
            market_value = (market_price * qty) if market_price is not None else None
            unrealized = compute_unrealized_pnl(qty=qty, avg_cost=avg_cost, market_price=market_price)
            cur.execute(
                '''
                INSERT INTO positions (
                  ticker, qty, avg_cost, market_price, market_value, unrealized_pnl, realized_pnl, updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (ticker, qty, avg_cost, market_price, market_value, unrealized, 0.0, utc_now()),
            )
            preview.append({'ticker': ticker, 'qty': qty, 'avg_cost': avg_cost, 'market_price': market_price, 'unrealized_pnl': unrealized})
    return {'ok': True, 'cycle_id': cycle_id, 'positions_count': len(preview), 'preview': preview[:10]}


if __name__ == '__main__':
    from packages.supervisor.common.db import connect
    run_id = new_run_id()
    started_at = utc_now()
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
                row = cur.fetchone()
                if not row:
                    raise RuntimeError('no_market_state_cycle')
                result = rebuild_positions(conn, cycle_id=row[0])
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_rebuild_positions', dataset_name='positions', status='complete', started_at=started_at, finished_at=finished_at, rows_written=result['positions_count'], rows_upserted=result['positions_count'], summary_json=result)
        print(json.dumps(to_jsonable(result), ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_rebuild_positions', dataset_name='positions', status='failed', started_at=started_at, finished_at=finished_at, errors_count=1, summary_json={'error': str(exc)})
        write_failure(failure_id=new_failure_id(), run_id=run_id, job_name='supervisor_rebuild_positions', stage='rebuild_positions', error_class=type(exc).__name__, error_message=str(exc), retryable=False)
        raise
