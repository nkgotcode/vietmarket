#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_cycle_id, new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.snapshots.common import get_market_context, to_jsonable
from packages.supervisor.snapshots.regime_builder import build_market_regime
from packages.supervisor.snapshots.sector_snapshot_builder import build_sector_snapshots
from packages.supervisor.snapshots.ticker_snapshot_builder import build_ticker_snapshots


def build_market_state() -> dict:
    cycle_id = new_cycle_id()
    created_at = utc_now()
    with connect() as conn:
        context = get_market_context(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO market_state_cycles (
                  cycle_id, source_health_snapshot_id, overall_status, freshness_status,
                  frontier_status, universe_count, regime_code, notes_json, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    cycle_id,
                    context.health.snapshot_id,
                    context.health.overall_status,
                    context.health.freshness_status,
                    'unknown',
                    0,
                    None,
                    json.dumps({'status': 'building'}, default=str),
                    created_at,
                ),
            )
        ticker_result = build_ticker_snapshots(conn, cycle_id=cycle_id, created_at=created_at, context=context)
        sector_result = build_sector_snapshots(conn, cycle_id=cycle_id, created_at=created_at, ticker_rows=ticker_result['rows'])
        regime_result = build_market_regime(
            conn,
            cycle_id=cycle_id,
            created_at=created_at,
            context=context,
            ticker_rows=ticker_result['rows'],
            sector_rows=sector_result['rows'],
        )
        notes_json = {
            'health': {
                'snapshot_id': context.health.snapshot_id,
                'overall_status': context.health.overall_status,
                'freshness_status': context.health.freshness_status,
                'blocking_issue_count': context.health.blocking_issue_count,
            },
            'watchlist_preview': ticker_result['watchlist_preview'],
            'sector_count': sector_result['count'],
        }
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE market_state_cycles
                   SET frontier_status = %s,
                       universe_count = %s,
                       regime_code = %s,
                       notes_json = %s
                 WHERE cycle_id = %s
                ''',
                (
                    regime_result['reasoning_json'].get('frontier_status', 'unknown'),
                    ticker_result['count'],
                    regime_result['market_regime'],
                    json.dumps(to_jsonable(notes_json), default=str),
                    cycle_id,
                ),
            )
            if context.health.snapshot_id:
                cur.execute(
                    'UPDATE system_health_snapshots SET cycle_id = %s WHERE snapshot_id = %s',
                    (cycle_id, context.health.snapshot_id),
                )
        return {
            'ok': True,
            'cycle_id': cycle_id,
            'created_at': created_at.isoformat(timespec='seconds'),
            'ticker_snapshot_count': ticker_result['count'],
            'sector_snapshot_count': sector_result['count'],
            'market_regime': regime_result['market_regime'],
            'regime_confidence': regime_result['confidence'],
            'frontier_status': regime_result['reasoning_json'].get('frontier_status'),
            'health_status': context.health.overall_status,
            'watchlist_preview': ticker_result['watchlist_preview'],
        }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_market_state()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_market_state',
            dataset_name='market_state',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('ticker_snapshot_count', 0) + result.get('sector_snapshot_count', 0) + 2,
            rows_upserted=result.get('ticker_snapshot_count', 0) + result.get('sector_snapshot_count', 0) + 2,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_market_state',
            dataset_name='market_state',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_market_state',
            stage='build_market_state',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
