#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_decision_id, new_failure_id, new_recommendation_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.snapshots.common import to_jsonable


def generate_recommendations() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
            cycle_row = cur.fetchone()
            if not cycle_row:
                raise RuntimeError('no_market_state_cycle')
            cycle_id = cycle_row[0]
            cur.execute(
                '''
                SELECT t.thesis_id, t.ticker, t.side, t.horizon, t.confidence, t.why_now,
                       t.supporting_evidence, t.contradicting_evidence, t.invalidation,
                       t.suggested_priority, t.notes,
                       c.total_score, c.total_confidence, c.ranking_bucket, c.blocking_flag
                FROM theses t
                JOIN candidate_rankings c ON c.cycle_id = t.cycle_id AND c.ticker = t.ticker
                WHERE t.cycle_id = %s
                ORDER BY c.blocking_flag ASC, c.total_score DESC, c.total_confidence DESC, t.ticker ASC
                ''',
                (cycle_id,),
            )
            rows = cur.fetchall()
            cur.execute('DELETE FROM supervisor_decisions WHERE cycle_id = %s AND decision_type = %s', (cycle_id, 'recommendation_generation'))
            cur.execute('DELETE FROM recommendations WHERE cycle_id = %s', (cycle_id,))
            now = utc_now()
            preview = []
            for row in rows:
                thesis_id, ticker, side, horizon, confidence, why_now, supporting, contradicting, invalidation, priority, notes, total_score, total_confidence, ranking_bucket, blocking_flag = row
                status = 'blocked' if blocking_flag else ('active' if ranking_bucket in ('high_conviction', 'actionable') else 'watch')
                summary = f"{ticker} is {status} with Phase 3 score {float(total_score or 0.0):.2f} and confidence {float(total_confidence or 0.0):.2f}"
                recommendation_json = {
                    'ticker': ticker,
                    'status': status,
                    'ranking_bucket': ranking_bucket,
                    'phase3_total_score': total_score,
                    'phase3_total_confidence': total_confidence,
                    'thesis_notes': notes,
                }
                recommendation_id = new_recommendation_id()
                cur.execute(
                    '''
                    INSERT INTO recommendations (
                      recommendation_id, cycle_id, thesis_id, ticker, status, side, horizon,
                      confidence, suggested_priority, summary, why_now, supporting_evidence,
                      contradicting_evidence, invalidation, recommendation_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        recommendation_id,
                        cycle_id,
                        thesis_id,
                        ticker,
                        status,
                        side,
                        horizon,
                        confidence,
                        priority,
                        summary,
                        why_now,
                        json.dumps(to_jsonable(supporting), default=str),
                        json.dumps(to_jsonable(contradicting), default=str),
                        json.dumps(to_jsonable(invalidation), default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        now,
                    ),
                )
                cur.execute(
                    '''
                    INSERT INTO supervisor_decisions (
                      decision_id, cycle_id, ticker, decision_type, input_packet_json,
                      raw_model_output_json, parsed_output_json, status, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        new_decision_id(),
                        cycle_id,
                        ticker,
                        'recommendation_generation',
                        json.dumps({'thesis_id': thesis_id, 'ranking_bucket': ranking_bucket, 'blocking_flag': blocking_flag}, default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        'complete',
                        now,
                    ),
                )
                preview.append({'ticker': ticker, 'status': status, 'side': side, 'confidence': confidence})
        return {'ok': True, 'cycle_id': cycle_id, 'recommendation_count': len(rows), 'preview': preview[:10]}


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = generate_recommendations()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_recommendations',
            dataset_name='recommendations',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('recommendation_count', 0) * 2,
            rows_upserted=result.get('recommendation_count', 0) * 2,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_recommendations',
            dataset_name='recommendations',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_generate_recommendations',
            stage='generate_recommendations',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
