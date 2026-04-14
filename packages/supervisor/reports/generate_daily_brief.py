#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_brief_id, new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.snapshots.common import to_jsonable


def generate_daily_brief() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT c.cycle_id, r.market_regime, r.confidence, r.breadth_state, r.trend_state,
                       r.liquidity_state, r.event_pressure_state
                FROM market_state_cycles c
                JOIN market_regime_snapshots r ON r.cycle_id = c.cycle_id
                ORDER BY c.created_at DESC
                LIMIT 1
                '''
            )
            regime = cur.fetchone()
            if not regime:
                raise RuntimeError('no_market_state_cycle')
            cycle_id, market_regime, confidence, breadth_state, trend_state, liquidity_state, event_pressure_state = regime
            cur.execute(
                '''
                SELECT ticker, status, side, confidence, suggested_priority, summary
                FROM recommendations
                WHERE cycle_id = %s
                ORDER BY status ASC, suggested_priority ASC, confidence DESC, ticker ASC
                LIMIT 10
                ''',
                (cycle_id,),
            )
            rec_rows = [
                {
                    'ticker': row[0],
                    'status': row[1],
                    'side': row[2],
                    'confidence': row[3],
                    'suggested_priority': row[4],
                    'summary': row[5],
                }
                for row in cur.fetchall()
            ]
            title = f'Daily brief — {market_regime}'
            summary_text = (
                f"Regime {market_regime} (confidence {float(confidence or 0.0):.2f}); "
                f"breadth {breadth_state}, trend {trend_state}, liquidity {liquidity_state}, event pressure {event_pressure_state}."
            )
            brief_json = {
                'market_regime': market_regime,
                'confidence': confidence,
                'breadth_state': breadth_state,
                'trend_state': trend_state,
                'liquidity_state': liquidity_state,
                'event_pressure_state': event_pressure_state,
                'top_recommendations': rec_rows,
            }
            now = utc_now()
            cur.execute('DELETE FROM daily_briefs WHERE cycle_id = %s AND brief_type = %s', (cycle_id, 'daily'))
            cur.execute(
                '''
                INSERT INTO daily_briefs (
                  brief_id, cycle_id, brief_type, title, summary_text, brief_json, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    new_brief_id(),
                    cycle_id,
                    'daily',
                    title,
                    summary_text,
                    json.dumps(to_jsonable(brief_json), default=str),
                    now,
                ),
            )
        return {'ok': True, 'cycle_id': cycle_id, 'brief_type': 'daily', 'recommendation_count': len(rec_rows), 'title': title}


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = generate_daily_brief()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_daily_brief',
            dataset_name='daily_briefs',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=1,
            rows_upserted=1,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_daily_brief',
            dataset_name='daily_briefs',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_generate_daily_brief',
            stage='generate_daily_brief',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
