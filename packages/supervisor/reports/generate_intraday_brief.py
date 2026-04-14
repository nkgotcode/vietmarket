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


def generate_intraday_brief() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT c.cycle_id, r.market_regime, r.confidence,
                       c.frontier_status, c.overall_status, c.freshness_status
                FROM market_state_cycles c
                JOIN market_regime_snapshots r ON r.cycle_id = c.cycle_id
                ORDER BY c.created_at DESC
                LIMIT 1
                '''
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError('no_market_state_cycle')
            cycle_id, market_regime, confidence, frontier_status, overall_status, freshness_status = row
            cur.execute(
                '''
                SELECT ticker, total_score, total_confidence, ranking_bucket
                FROM candidate_rankings
                WHERE cycle_id = %s AND blocking_flag = false
                ORDER BY total_score DESC, total_confidence DESC, ticker ASC
                LIMIT 5
                ''',
                (cycle_id,),
            )
            candidate_rows = [
                {'ticker': r[0], 'total_score': r[1], 'total_confidence': r[2], 'ranking_bucket': r[3]}
                for r in cur.fetchall()
            ]
            title = f'Intraday brief — {market_regime}'
            summary_text = (
                f"Intraday regime {market_regime} (confidence {float(confidence or 0.0):.2f}), "
                f"system {overall_status}/{freshness_status}, frontier {frontier_status}."
            )
            brief_json = {
                'market_regime': market_regime,
                'confidence': confidence,
                'frontier_status': frontier_status,
                'overall_status': overall_status,
                'freshness_status': freshness_status,
                'top_candidates': candidate_rows,
            }
            now = utc_now()
            cur.execute('DELETE FROM daily_briefs WHERE cycle_id = %s AND brief_type = %s', (cycle_id, 'intraday'))
            cur.execute(
                '''
                INSERT INTO daily_briefs (
                  brief_id, cycle_id, brief_type, title, summary_text, brief_json, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    new_brief_id(), cycle_id, 'intraday', title, summary_text,
                    json.dumps(to_jsonable(brief_json), default=str), now,
                ),
            )
        return {'ok': True, 'cycle_id': cycle_id, 'brief_type': 'intraday', 'candidate_count': len(candidate_rows), 'title': title}


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = generate_intraday_brief()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_intraday_brief',
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
            job_name='supervisor_generate_intraday_brief',
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
            job_name='supervisor_generate_intraday_brief',
            stage='generate_intraday_brief',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
