from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from typing import Any

import psycopg2.extras

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.policy.checks import (
    check_confidence,
    check_event_blackout,
    check_liquidity,
    check_recommendation_status,
    check_system_health,
)
from packages.supervisor.policy.default_rules import DEFAULT_RISK_LIMITS
from packages.supervisor.snapshots.common import to_jsonable


def _ensure_limits(conn) -> None:
    with conn.cursor() as cur:
        for name, value in DEFAULT_RISK_LIMITS.items():
            cur.execute(
                '''
                INSERT INTO risk_limits (limit_name, limit_value, notes_json, created_at, updated_at)
                VALUES (%s,%s,%s,now(),now())
                ON CONFLICT (limit_name) DO UPDATE SET
                  limit_value = EXCLUDED.limit_value,
                  updated_at = now()
                ''',
                (name, value, json.dumps({'source': 'phase5_default'})),
            )


def _latest_rows(conn) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT r.recommendation_id,
                   r.cycle_id,
                   r.ticker,
                   coalesce(ds.final_state, p.promotion_state, r.status) AS recommendation_status,
                   ds.analytical_state,
                   ds.policy_blocked,
                   r.side,
                   coalesce((r.recommendation_json->>'forecast_reliability')::double precision,
                            (r.recommendation_json->>'model_confidence')::double precision,
                            r.confidence,
                            0) AS confidence,
                   r.suggested_priority,
                   c.overall_status AS cycle_overall_status,
                   t.liquidity_bucket,
                   t.corporate_action_flag AS has_corporate_action,
                   coalesce((r.recommendation_json->>'execution_reliability')::double precision,
                            d.execution_score / 100.0,
                            0) AS liquidity_score,
                   t.sector,
                   coalesce(ds.paper_eligible, d.paper_eligible, false) AS paper_eligible,
                   d.decision_score,
                   d.score_version
            FROM recommendations r
            JOIN market_state_cycles c ON c.cycle_id = r.cycle_id
            LEFT JOIN promotion_decisions p
              ON p.recommendation_id = r.recommendation_id
            LEFT JOIN decision_states_v2 ds
              ON ds.cycle_id = r.cycle_id AND ds.ticker = r.ticker
             AND ds.grade_version = (SELECT grade_version FROM grade_versions ORDER BY created_at DESC LIMIT 1)
            LEFT JOIN ticker_snapshots t ON t.cycle_id = r.cycle_id AND t.ticker = r.ticker
            LEFT JOIN decision_scores d
              ON d.cycle_id = r.cycle_id AND d.ticker = r.ticker
             AND d.score_version = (SELECT score_version FROM score_versions ORDER BY created_at DESC LIMIT 1)
            WHERE r.cycle_id = (SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1)
            ORDER BY coalesce(ds.paper_eligible, d.paper_eligible, false) DESC, coalesce(d.decision_score, 0) DESC, r.ticker ASC
            '''
        )
        return [dict(row) for row in cur.fetchall()]


def evaluate_policy() -> dict[str, Any]:
    with connect() as conn:
        _ensure_limits(conn)
        rows = _latest_rows(conn)
        if not rows:
            raise RuntimeError('no_recommendations_for_latest_cycle')
        cycle_id = rows[0]['cycle_id']
        with conn.cursor() as cur:
            cur.execute('DELETE FROM policy_results WHERE cycle_id = %s', (cycle_id,))
            preview = []
            active_count = 0
            for row in rows:
                checks = [
                    check_system_health(row),
                    check_recommendation_status(row),
                    check_confidence(row, floor=DEFAULT_RISK_LIMITS['confidence_floor']),
                    check_liquidity(row, minimum_score=DEFAULT_RISK_LIMITS['min_liquidity_score']),
                    check_event_blackout(row),
                ]
                blocking = any(item['blocking'] and not item['passed'] for item in checks)
                overall = 'blocked' if blocking else ('approved' if bool(row.get('paper_eligible')) else 'monitor')
                if overall == 'approved':
                    active_count += 1
                cur.execute(
                    '''
                    INSERT INTO policy_results (
                      cycle_id, ticker, recommendation_id, overall_result, blocking_flag,
                      checks_json, summary_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        cycle_id,
                        row['ticker'],
                        row['recommendation_id'],
                        overall,
                        blocking,
                        json.dumps(to_jsonable(checks), default=str),
                        json.dumps({'sector': row.get('sector'), 'liquidity_bucket': row.get('liquidity_bucket'), 'score_version': row.get('score_version'), 'decision_score': row.get('decision_score')}, default=str),
                        utc_now(),
                    ),
                )
                preview.append({'ticker': row['ticker'], 'overall_result': overall, 'blocking_flag': blocking})
        return {'ok': True, 'cycle_id': cycle_id, 'policy_count': len(rows), 'approved_count': active_count, 'preview': preview[:10]}


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = evaluate_policy()
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_evaluate_policy', dataset_name='policy_results', status='complete', started_at=started_at, finished_at=finished_at, rows_written=result['policy_count'], rows_upserted=result['policy_count'], summary_json=result)
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(run_id=run_id, job_name='supervisor_evaluate_policy', dataset_name='policy_results', status='failed', started_at=started_at, finished_at=finished_at, errors_count=1, summary_json={'error': str(exc)})
        write_failure(failure_id=new_failure_id(), run_id=run_id, job_name='supervisor_evaluate_policy', stage='evaluate_policy', error_class=type(exc).__name__, error_message=str(exc), retryable=False)
        raise
