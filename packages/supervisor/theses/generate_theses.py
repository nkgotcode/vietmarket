#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_decision_id, new_failure_id, new_run_id, new_thesis_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.recommendations.parse_structured_output import normalize_generated_object
from packages.supervisor.snapshots.common import to_jsonable
from packages.supervisor.theses.build_supervisor_packet import build_supervisor_packet


def _build_generated_thesis(candidate: dict) -> dict:
    ranking_bucket = candidate.get('ranking_bucket') or 'watch'
    blocking = bool(candidate.get('blocking_flag'))
    confidence = float(candidate.get('total_confidence') or 0.0)
    side = 'long' if ranking_bucket in {'high_conviction', 'actionable'} and not blocking else 'watch'
    if blocking:
        side = 'avoid'
    signals = candidate.get('signals') or []
    supportive = []
    contradictory = []
    strongest = None
    weakest = None
    for signal in signals:
        entry = {
            'signal_family': signal.get('signal_family'),
            'score_normalized': signal.get('score_normalized'),
            'confidence': signal.get('confidence'),
            'blocking_flag': signal.get('blocking_flag'),
        }
        if strongest is None or float(signal.get('score_normalized') or 0.0) > float(strongest.get('score_normalized') or 0.0):
            strongest = entry
        if weakest is None or float(signal.get('score_normalized') or 0.0) < float(weakest.get('score_normalized') or 0.0):
            weakest = entry
        if entry['blocking_flag'] or float(entry['score_normalized'] or 0.0) < 0.35:
            contradictory.append(entry)
        elif float(entry['score_normalized'] or 0.0) >= 0.55:
            supportive.append(entry)
    why_now = f"{candidate['ticker']} is ranked {ranking_bucket} with total score {float(candidate.get('total_score') or 0.0):.2f}"
    if strongest:
        why_now += f", led by {strongest['signal_family']}"
    generated = {
        'ticker': candidate['ticker'],
        'thesis_type': 'signal_synthesis',
        'side': side,
        'horizon': 'swing_5d',
        'confidence': round(confidence, 6),
        'why_now': why_now,
        'supporting_evidence': supportive[:4],
        'contradicting_evidence': contradictory[:4],
        'invalidation': {
            'ranking_bucket_change': 'drop_below_watch',
            'risk_blocking_flag': True,
            'weakest_signal_family': weakest['signal_family'] if weakest else None,
        },
        'suggested_priority': max(0, 100 - int(float(candidate.get('total_score') or 0.0))),
        'notes': f"Deterministic Phase 4 thesis generated from Phase 3 signals for {candidate['ticker']}",
    }
    return normalize_generated_object(generated)


def generate_theses() -> dict:
    with connect() as conn:
        packet = build_supervisor_packet(conn)
        cycle_id = packet['cycle']['cycle_id']
        candidates = packet.get('candidates') or []
        now = utc_now()
        with conn.cursor() as cur:
            cur.execute('DELETE FROM supervisor_decisions WHERE cycle_id = %s AND decision_type = %s', (cycle_id, 'thesis_generation'))
            cur.execute('DELETE FROM theses WHERE cycle_id = %s', (cycle_id,))
            inserted = []
            for candidate in candidates:
                raw_output = _build_generated_thesis(candidate)
                thesis_id = new_thesis_id()
                cur.execute(
                    '''
                    INSERT INTO theses (
                      thesis_id, cycle_id, ticker, thesis_type, side, horizon, confidence,
                      why_now, supporting_evidence, contradicting_evidence, invalidation,
                      suggested_priority, notes, raw_output_json, normalized_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        thesis_id,
                        cycle_id,
                        raw_output['ticker'],
                        raw_output['thesis_type'],
                        raw_output['side'],
                        raw_output['horizon'],
                        raw_output['confidence'],
                        raw_output['why_now'],
                        json.dumps(to_jsonable(raw_output['supporting_evidence']), default=str),
                        json.dumps(to_jsonable(raw_output['contradicting_evidence']), default=str),
                        json.dumps(to_jsonable(raw_output['invalidation']), default=str),
                        raw_output['suggested_priority'],
                        raw_output['notes'],
                        json.dumps(to_jsonable(raw_output), default=str),
                        json.dumps(to_jsonable(raw_output), default=str),
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
                        raw_output['ticker'],
                        'thesis_generation',
                        json.dumps(to_jsonable(candidate), default=str),
                        json.dumps(to_jsonable(raw_output), default=str),
                        json.dumps(to_jsonable(raw_output), default=str),
                        'complete',
                        now,
                    ),
                )
                inserted.append({'thesis_id': thesis_id, 'ticker': raw_output['ticker'], 'side': raw_output['side'], 'confidence': raw_output['confidence']})
        return {
            'ok': True,
            'cycle_id': cycle_id,
            'thesis_count': len(candidates),
            'preview': inserted[:10],
        }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = generate_theses()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_theses',
            dataset_name='theses',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('thesis_count', 0) * 2,
            rows_upserted=result.get('thesis_count', 0) * 2,
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_generate_theses',
            dataset_name='theses',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_generate_theses',
            stage='generate_theses',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
