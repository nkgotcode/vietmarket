#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_issue_id, new_run_id, new_snapshot_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.portfolio.fill_simulator import simulate_fill_price, simulate_fill_qty
from packages.supervisor.portfolio.position_book import rebuild_positions
from packages.supervisor.snapshots.common import to_jsonable


def run_paper_portfolio_cycle() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
            row = cur.fetchone()
            if not row:
                raise RuntimeError('no_market_state_cycle')
            cycle_id = row[0]
            cur.execute('DELETE FROM execution_intents WHERE cycle_id = %s', (cycle_id,))
            cur.execute('DELETE FROM paper_orders WHERE cycle_id = %s', (cycle_id,))
            cur.execute('DELETE FROM portfolio_snapshots WHERE cycle_id = %s', (cycle_id,))
            cur.execute(
                '''
                SELECT a.cycle_id, a.ticker, a.recommendation_id, a.admission_status,
                       r.side, r.confidence, r.suggested_priority,
                       t.price_last
                FROM paper_trade_admissions a
                JOIN recommendations r ON r.recommendation_id = a.recommendation_id
                LEFT JOIN ticker_snapshots t ON t.cycle_id = a.cycle_id AND t.ticker = a.ticker
                WHERE a.cycle_id = %s
                ORDER BY a.admission_status ASC, r.suggested_priority ASC, r.confidence DESC, a.ticker ASC
                ''',
                (cycle_id,),
            )
            rows = cur.fetchall()
            created = []
            cash_balance = 1_000_000_000.0
            for idx, (cycle_id, ticker, recommendation_id, admission_status, side, confidence, suggested_priority, price_last) in enumerate(rows[:5], start=1):
                if admission_status != 'admitted' or not price_last:
                    continue
                intent_id = f'intent_{new_snapshot_id()}'
                qty = max(1.0, round((25_000_000.0 / float(price_last)), 2))
                cur.execute(
                    '''
                    INSERT INTO execution_intents (intent_id, cycle_id, recommendation_id, ticker, intent_status, side, target_qty, reference_price, notes_json, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (intent_id, cycle_id, recommendation_id, ticker, 'approved', side, qty, price_last, json.dumps({'confidence': confidence, 'priority': suggested_priority, 'admission_status': admission_status}), utc_now()),
                )
                paper_order_id = f'porder_{new_snapshot_id()}'
                cur.execute(
                    '''
                    INSERT INTO paper_orders (paper_order_id, intent_id, cycle_id, ticker, order_status, side, qty, limit_price, submitted_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (paper_order_id, intent_id, cycle_id, ticker, 'filled', side, qty, price_last, utc_now(), utc_now()),
                )
                fill_qty = simulate_fill_qty(qty)
                fill_price = simulate_fill_price(price_last)
                cash_balance -= fill_qty * fill_price
                cur.execute(
                    '''
                    INSERT INTO paper_fills (paper_fill_id, paper_order_id, ticker, fill_qty, fill_price, filled_at, notes_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (f'pfill_{new_snapshot_id()}', paper_order_id, ticker, fill_qty, fill_price, utc_now(), json.dumps({'source': 'deterministic_fill_simulator'})),
                )
                cur.execute(
                    '''
                    INSERT INTO position_events (event_id, ticker, event_type, qty_delta, price, related_order_id, notes_json, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (f'pevent_{new_snapshot_id()}', ticker, 'paper_fill', fill_qty, fill_price, paper_order_id, json.dumps({'intent_id': intent_id}), utc_now()),
                )
                created.append({'ticker': ticker, 'qty': fill_qty, 'fill_price': fill_price, 'paper_order_id': paper_order_id})
            position_result = rebuild_positions(conn, cycle_id=cycle_id)
            cur.execute('SELECT coalesce(sum(market_value),0), coalesce(sum(unrealized_pnl),0), count(*) FROM positions')
            mv, upnl, cnt = cur.fetchone()
            cur.execute(
                '''
                INSERT INTO portfolio_snapshots (snapshot_id, cycle_id, cash_balance, gross_exposure, net_exposure, market_value, unrealized_pnl, realized_pnl, positions_count, snapshot_json, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (f'portsnap_{new_snapshot_id()}', cycle_id, cash_balance, float(mv or 0.0), float(mv or 0.0), float(mv or 0.0), float(upnl or 0.0), 0.0, int(cnt or 0), json.dumps({'created_orders': created, 'position_preview': position_result['preview']}), utc_now()),
            )
        return {'ok': True, 'cycle_id': cycle_id, 'intent_count': len(created), 'paper_order_count': len(created), 'positions_count': position_result['positions_count'], 'preview': created}


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = run_paper_portfolio_cycle()
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_run_paper_portfolio_cycle', dataset_name='portfolio', status='complete', started_at=started_at, finished_at=finished_at, rows_written=result['paper_order_count'] + result['positions_count'], rows_upserted=result['paper_order_count'] + result['positions_count'], summary_json=result)
        print(json.dumps(to_jsonable(result), ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_run_paper_portfolio_cycle', dataset_name='portfolio', status='failed', started_at=started_at, finished_at=finished_at, errors_count=1, summary_json={'error': str(exc)})
        write_failure(failure_id=new_failure_id(), run_id=run_id, job_name='supervisor_run_paper_portfolio_cycle', stage='run_paper_portfolio_cycle', error_class=type(exc).__name__, error_message=str(exc), retryable=False)
        raise
