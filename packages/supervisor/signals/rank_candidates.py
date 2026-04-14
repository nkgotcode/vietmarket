#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.signals.common import DEFAULT_POLICY, load_policy_weights, load_signal_rows, replace_candidate_rankings
from packages.supervisor.snapshots.common import to_jsonable


def _bucket(total_score: float, total_confidence: float, blocking_flag: bool) -> str:
    if blocking_flag:
        return 'blocked'
    if total_score >= 75 and total_confidence >= 0.65:
        return 'high_conviction'
    if total_score >= 60 and total_confidence >= 0.55:
        return 'actionable'
    if total_score >= 45:
        return 'watch'
    return 'avoid'


def rank_candidates() -> dict:
    with connect() as conn:
        weights = load_policy_weights(conn)
        family_rows = load_signal_rows(conn, cycle_id=_latest_cycle_id(conn))
        if not family_rows:
            raise RuntimeError('no_signal_scores_for_latest_cycle')
        cycle_id = family_rows[0]['cycle_id']
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in family_rows:
            grouped[row['ticker']].append(row)

        now = utc_now()
        output_rows = []
        for ticker, rows in grouped.items():
            weighted_score = 0.0
            weighted_confidence = 0.0
            weight_total = 0.0
            family_breakdown = {}
            blocking_flag = any(bool(row.get('blocking_flag')) for row in rows)
            strongest = None
            weakest = None
            for row in rows:
                family = row['signal_family']
                weight = float(weights.get(family, 0.0))
                normalized = float(row.get('score_normalized') or 0.0)
                confidence = float(row.get('confidence') or 0.0)
                weighted_score += normalized * weight
                weighted_confidence += confidence * weight
                weight_total += weight
                family_breakdown[family] = {
                    'score_normalized': normalized,
                    'confidence': confidence,
                    'blocking_flag': bool(row.get('blocking_flag')),
                    'reason_json': row.get('reason_json') or {},
                }
                score_for_compare = normalized * confidence
                if strongest is None or score_for_compare > strongest[1]:
                    strongest = (family, score_for_compare)
                if weakest is None or score_for_compare < weakest[1]:
                    weakest = (family, score_for_compare)
            total_score = round((weighted_score / weight_total) * 100.0 if weight_total else 0.0, 4)
            total_confidence = round((weighted_confidence / weight_total) if weight_total else 0.0, 6)
            output_rows.append(
                {
                    'cycle_id': cycle_id,
                    'ticker': ticker,
                    'total_score': total_score,
                    'total_confidence': total_confidence,
                    'ranking_bucket': _bucket(total_score, total_confidence, blocking_flag),
                    'blocking_flag': blocking_flag,
                    'ranking_reason_json': to_jsonable(
                        {
                            'weights': weights,
                            'family_breakdown': family_breakdown,
                            'strongest_family': strongest[0] if strongest else None,
                            'weakest_family': weakest[0] if weakest else None,
                            'policy_name': DEFAULT_POLICY['policy_name'],
                        }
                    ),
                    'created_at': now,
                }
            )

        output_rows.sort(key=lambda row: (row['blocking_flag'], -row['total_score'], -row['total_confidence'], row['ticker']))
        replace_candidate_rankings(conn, cycle_id=cycle_id, rows=output_rows)
        return {
            'ok': True,
            'cycle_id': cycle_id,
            'candidate_count': len(output_rows),
            'preview': [
                {
                    'ticker': row['ticker'],
                    'total_score': row['total_score'],
                    'total_confidence': row['total_confidence'],
                    'ranking_bucket': row['ranking_bucket'],
                    'blocking_flag': row['blocking_flag'],
                }
                for row in output_rows[:10]
            ],
        }


def _latest_cycle_id(conn) -> str:
    with conn.cursor() as cur:
        cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
        row = cur.fetchone()
    if not row:
        raise RuntimeError('no_market_state_cycle')
    return row[0]


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = rank_candidates()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_rank_candidates',
            dataset_name='candidate_rankings',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('candidate_count', 0),
            rows_upserted=result.get('candidate_count', 0),
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_rank_candidates',
            dataset_name='candidate_rankings',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_rank_candidates',
            stage='rank_candidates',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
