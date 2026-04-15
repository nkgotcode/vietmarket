#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import psycopg2.extras

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_admission_id, new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.policy.default_rules import DEFAULT_PROMOTION_POLICY
from packages.supervisor.snapshots.common import to_jsonable


def _ensure_policy(conn) -> str:
    version = DEFAULT_PROMOTION_POLICY['promotion_policy_version']
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO promotion_policy_versions (
              promotion_policy_version, status, paper_trading_enabled, thresholds_json, notes_json, created_at
            ) VALUES (%s,%s,%s,%s,%s,now())
            ON CONFLICT (promotion_policy_version) DO UPDATE SET
              status = EXCLUDED.status,
              paper_trading_enabled = EXCLUDED.paper_trading_enabled,
              thresholds_json = EXCLUDED.thresholds_json,
              notes_json = EXCLUDED.notes_json
            ''',
            (
                version,
                'active',
                DEFAULT_PROMOTION_POLICY['paper_trading_enabled'],
                json.dumps(DEFAULT_PROMOTION_POLICY['thresholds']),
                json.dumps(DEFAULT_PROMOTION_POLICY['notes']),
            ),
        )
    return version


def evaluate_promotion_gate() -> dict:
    with connect() as conn:
        policy_version = _ensure_policy(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT p.recommendation_id,
                       p.cycle_id,
                       p.ticker,
                       p.promotion_state,
                       p.paper_eligible,
                       r.score_version,
                       r.alpha_score,
                       r.quality_score,
                       r.risk_score,
                       r.execution_score,
                       r.decision_score,
                       r.model_confidence,
                       r.evidence_confidence,
                       r.execution_confidence,
                       pr.overall_result AS policy_result,
                       v.paper_trading_enabled,
                       v.thresholds_json
                FROM promotion_decisions p
                JOIN recommendation_scorecards r ON r.recommendation_id = p.recommendation_id
                LEFT JOIN policy_results pr ON pr.recommendation_id = p.recommendation_id
                JOIN promotion_policy_versions v ON v.promotion_policy_version = %s
                WHERE p.cycle_id = (SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1)
                ORDER BY p.paper_eligible DESC, r.decision_score DESC, p.ticker ASC
                ''',
                (policy_version,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            if not rows:
                raise RuntimeError('no_promotion_decisions_for_latest_cycle')
            cycle_id = rows[0]['cycle_id']
            cur.execute('DELETE FROM paper_trade_admissions WHERE cycle_id = %s AND promotion_policy_version = %s', (cycle_id, policy_version))
            preview = []
            admitted = 0
            for row in rows:
                thresholds = row.get('thresholds_json') or {}
                reasons = {
                    'promotion_state': row.get('promotion_state'),
                    'paper_eligible': bool(row.get('paper_eligible')),
                    'policy_result': row.get('policy_result'),
                    'paper_trading_enabled': bool(row.get('paper_trading_enabled')),
                }
                meets_thresholds = (
                    float(row.get('decision_score') or 0.0) >= float(thresholds.get('decision_score', 0.0))
                    and float(row.get('model_confidence') or 0.0) >= float(thresholds.get('model_confidence', 0.0))
                    and float(row.get('evidence_confidence') or 0.0) >= float(thresholds.get('evidence_confidence', 0.0))
                    and float(row.get('execution_confidence') or 0.0) >= float(thresholds.get('execution_confidence', 0.0))
                    and float(row.get('risk_score') or 0.0) >= float(thresholds.get('risk_score', 0.0))
                    and float(row.get('execution_score') or 0.0) >= float(thresholds.get('execution_score', 0.0))
                )
                if not bool(row.get('paper_trading_enabled')):
                    admission_status = 'disabled'
                elif row.get('policy_result') != 'approved':
                    admission_status = 'blocked_policy'
                elif not bool(row.get('paper_eligible')):
                    admission_status = 'not_paper_eligible'
                elif not meets_thresholds:
                    admission_status = 'below_thresholds'
                else:
                    admission_status = 'admitted'
                    admitted += 1
                reasons['meets_thresholds'] = meets_thresholds
                cur.execute(
                    '''
                    INSERT INTO paper_trade_admissions (
                      admission_id, recommendation_id, cycle_id, ticker, score_version,
                      promotion_policy_version, admission_status, policy_result,
                      paper_trading_enabled, admission_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        new_admission_id(),
                        row['recommendation_id'],
                        cycle_id,
                        row['ticker'],
                        row['score_version'],
                        policy_version,
                        admission_status,
                        row.get('policy_result'),
                        bool(row.get('paper_trading_enabled')),
                        json.dumps(to_jsonable({**reasons, 'thresholds': thresholds}), default=str),
                        utc_now(),
                    ),
                )
                preview.append({'ticker': row['ticker'], 'admission_status': admission_status, 'paper_eligible': bool(row.get('paper_eligible'))})
        return {
            'ok': True,
            'cycle_id': cycle_id,
            'promotion_policy_version': policy_version,
            'admission_count': len(rows),
            'admitted_count': admitted,
            'preview': preview[:10],
        }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = evaluate_promotion_gate()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_evaluate_promotion_gate',
            dataset_name='paper_trade_admissions',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('admission_count', 0),
            rows_upserted=result.get('admission_count', 0),
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_evaluate_promotion_gate',
            dataset_name='paper_trade_admissions',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_evaluate_promotion_gate',
            stage='evaluate_promotion_gate',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
