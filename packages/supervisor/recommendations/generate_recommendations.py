#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_decision_id, new_failure_id, new_promotion_decision_id, new_recommendation_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.snapshots.common import to_jsonable


def _status_rank(state: str) -> int:
    order = {
        'paper_eligible': 0,
        'candidate': 1,
        'watch': 2,
        'research_only': 3,
        'blocked': 4,
        'retired': 5,
    }
    return order.get(state, 9)


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
                SELECT t.thesis_id,
                       t.ticker,
                       t.side,
                       t.horizon,
                       t.why_now,
                       t.supporting_evidence,
                       t.contradicting_evidence,
                       t.invalidation,
                       t.notes,
                       d.score_version,
                       d.alpha_score,
                       d.quality_score,
                       d.risk_score,
                       d.execution_score,
                       d.decision_score,
                       d.model_confidence,
                       d.evidence_confidence,
                       d.execution_confidence,
                       d.recommended_state,
                       d.paper_eligible,
                       d.block_reason_json,
                       d.score_json,
                       ds.analytical_state,
                       ds.final_state,
                       ds.paper_eligible AS grade_paper_eligible,
                       ds.policy_blocked,
                       ds.state_json
                FROM theses t
                JOIN decision_scores d
                  ON d.cycle_id = t.cycle_id AND d.ticker = t.ticker
                LEFT JOIN decision_states_v2 ds
                  ON ds.cycle_id = t.cycle_id AND ds.ticker = t.ticker
                 AND ds.grade_version = (SELECT grade_version FROM grade_versions ORDER BY created_at DESC LIMIT 1)
                WHERE t.cycle_id = %s
                  AND d.score_version = (SELECT score_version FROM score_versions ORDER BY created_at DESC LIMIT 1)
                ORDER BY coalesce(ds.paper_eligible, d.paper_eligible) DESC, d.decision_score DESC, d.model_confidence DESC, t.ticker ASC
                ''',
                (cycle_id,),
            )
            rows = cur.fetchall()
            cur.execute('DELETE FROM supervisor_decisions WHERE cycle_id = %s AND decision_type = %s', (cycle_id, 'recommendation_generation'))
            cur.execute('DELETE FROM promotion_decisions WHERE cycle_id = %s', (cycle_id,))
            cur.execute('DELETE FROM recommendation_scorecards WHERE cycle_id = %s', (cycle_id,))
            cur.execute('DELETE FROM recommendations WHERE cycle_id = %s', (cycle_id,))
            now = utc_now()
            preview = []
            for row in rows:
                (
                    thesis_id,
                    ticker,
                    side,
                    horizon,
                    why_now,
                    supporting,
                    contradicting,
                    invalidation,
                    notes,
                    score_version,
                    alpha_score,
                    quality_score,
                    risk_score,
                    execution_score,
                    decision_score,
                    model_confidence,
                    evidence_confidence,
                    execution_confidence,
                    recommended_state,
                    paper_eligible,
                    block_reason_json,
                    score_json,
                    analytical_state,
                    final_state,
                    grade_paper_eligible,
                    policy_blocked,
                    state_json,
                ) = row

                grade_state = dict(state_json or {})
                status = str(final_state or recommended_state)
                paper_eligible = bool(grade_paper_eligible) if grade_paper_eligible is not None else bool(paper_eligible)
                confidence = float(grade_state.get('forecast_reliability') or model_confidence or 0.0)
                suggested_priority = max(0, 100 - int(float(decision_score or 0.0)))
                summary = (
                    f"{ticker} is {status} with decision score {float(decision_score or 0.0):.2f}, "
                    f"alpha {float(alpha_score or 0.0):.2f}, risk {float(risk_score or 0.0):.2f}, "
                    f"execution {float(execution_score or 0.0):.2f}"
                )
                recommendation_json = {
                    'ticker': ticker,
                    'status': status,
                    'analytical_state': analytical_state or recommended_state,
                    'policy_blocked': bool(policy_blocked),
                    'score_version': score_version,
                    'paper_eligible': bool(paper_eligible),
                    'alpha_score': alpha_score,
                    'quality_score': quality_score,
                    'risk_score': risk_score,
                    'execution_score': execution_score,
                    'decision_score': decision_score,
                    'model_confidence': model_confidence,
                    'evidence_confidence': evidence_confidence,
                    'execution_confidence': execution_confidence,
                    'Opportunity Grade': grade_state.get('Opportunity Grade'),
                    'Evidence Grade': grade_state.get('Evidence Grade'),
                    'Tradability Grade': grade_state.get('Tradability Grade'),
                    'Risk Containment Grade': grade_state.get('Risk Containment Grade'),
                    'forecast_reliability': grade_state.get('forecast_reliability'),
                    'evidence_reliability': grade_state.get('evidence_reliability'),
                    'execution_reliability': grade_state.get('execution_reliability'),
                    'block_reason_json': block_reason_json or {},
                    'score_json': score_json or {},
                    'state_json': grade_state,
                    'thesis_notes': notes,
                }
                why_now_text = (
                    f"{why_now}; state {status}, analytical_state {analytical_state or recommended_state}, "
                    f"Opportunity Grade {grade_state.get('Opportunity Grade')}, Tradability Grade {grade_state.get('Tradability Grade')}, "
                    f"forecast reliability {float(grade_state.get('forecast_reliability') or confidence or 0.0):.2f}"
                )
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
                        suggested_priority,
                        summary,
                        why_now_text,
                        json.dumps(to_jsonable(supporting), default=str),
                        json.dumps(to_jsonable(contradicting), default=str),
                        json.dumps(to_jsonable(invalidation), default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        now,
                    ),
                )
                cur.execute(
                    '''
                    INSERT INTO recommendation_scorecards (
                      recommendation_id, cycle_id, ticker, score_version, alpha_score, quality_score,
                      risk_score, execution_score, decision_score, model_confidence,
                      evidence_confidence, execution_confidence, scorecard_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        recommendation_id,
                        cycle_id,
                        ticker,
                        score_version,
                        alpha_score,
                        quality_score,
                        risk_score,
                        execution_score,
                        decision_score,
                        model_confidence,
                        evidence_confidence,
                        execution_confidence,
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        now,
                    ),
                )
                cur.execute(
                    '''
                    INSERT INTO promotion_decisions (
                      promotion_decision_id, recommendation_id, cycle_id, ticker, score_version,
                      promotion_state, paper_eligible, decision_json, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ''',
                    (
                        new_promotion_decision_id(),
                        recommendation_id,
                        cycle_id,
                        ticker,
                        score_version,
                        recommended_state,
                        bool(paper_eligible),
                        json.dumps(
                            to_jsonable(
                                {
                                    'decision_score': decision_score,
                                    'model_confidence': model_confidence,
                                    'evidence_confidence': evidence_confidence,
                                    'execution_confidence': execution_confidence,
                                    'analytical_state': analytical_state or recommended_state,
                                    'policy_blocked': bool(policy_blocked),
                                    'Opportunity Grade': grade_state.get('Opportunity Grade'),
                                    'Tradability Grade': grade_state.get('Tradability Grade'),
                                    'block_reason_json': block_reason_json or {},
                                    'score_json': score_json or {},
                                    'state_json': grade_state,
                                }
                            ),
                            default=str,
                        ),
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
                        json.dumps({'thesis_id': thesis_id, 'score_version': score_version, 'recommended_state': recommended_state, 'paper_eligible': paper_eligible}, default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        json.dumps(to_jsonable(recommendation_json), default=str),
                        'complete',
                        now,
                    ),
                )
                preview.append({'ticker': ticker, 'status': status, 'confidence': confidence, 'decision_score': decision_score, 'paper_eligible': bool(paper_eligible)})
        preview.sort(key=lambda item: (_status_rank(str(item['status'])), -float(item['decision_score'] or 0.0), item['ticker']))
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
