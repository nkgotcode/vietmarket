#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.grading.common import VERSION, latest_cycle_context


def _analytical_state(opportunity: str, evidence: str, tradability: str, risk: str, forecast_reliability: float) -> tuple[str, bool]:
    strong_opportunity = opportunity in {'A', 'B'}
    usable_evidence = evidence in {'strong', 'good'}
    usable_tradability = tradability in {'excellent', 'good'}
    usable_risk = risk in {'contained', 'acceptable'}
    strong_reliability = forecast_reliability >= 0.62
    paper_eligible = strong_opportunity and usable_evidence and usable_tradability and usable_risk and strong_reliability
    if paper_eligible:
        return 'paper_eligible', True
    if strong_opportunity and usable_evidence and usable_risk:
        return 'candidate', False
    if strong_opportunity or opportunity == 'C':
        return 'watch', False
    return 'research_only', False


def build_decision_states() -> dict:
    with connect() as conn:
        ctx = latest_cycle_context(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT o.ticker,
                       o.grade_label AS opportunity_grade,
                       e.grade_label AS evidence_grade,
                       t.grade_label AS tradability_grade,
                       r.grade_label AS risk_grade,
                       rs.forecast_reliability,
                       rs.evidence_reliability,
                       rs.execution_reliability,
                       t.capacity_band,
                       t.execution_cost_estimate,
                       o.grade_percentile
                FROM opportunity_grades o
                JOIN evidence_grades e
                  ON e.cycle_id = o.cycle_id AND e.ticker = o.ticker AND e.grade_version = o.grade_version
                JOIN tradability_grades t
                  ON t.cycle_id = o.cycle_id AND t.ticker = o.ticker AND t.grade_version = o.grade_version
                JOIN risk_containment_grades r
                  ON r.cycle_id = o.cycle_id AND r.ticker = o.ticker AND r.grade_version = o.grade_version
                JOIN reliability_snapshots rs
                  ON rs.cycle_id = o.cycle_id AND rs.ticker = o.ticker AND rs.grade_version = o.grade_version
                WHERE o.cycle_id = %s AND o.grade_version = %s
                ORDER BY o.ticker ASC
                ''',
                (ctx.cycle_id, VERSION),
            )
            rows = cur.fetchall()

        if not rows:
            raise RuntimeError('no_grade_plane_rows_for_latest_cycle')

        payload = []
        preview = []
        now = utc_now()
        for row in rows:
            (
                ticker,
                opportunity_grade,
                evidence_grade,
                tradability_grade,
                risk_grade,
                forecast_reliability,
                evidence_reliability,
                execution_reliability,
                capacity_band,
                execution_cost_estimate,
                grade_percentile,
            ) = row
            forecast_reliability = float(forecast_reliability or 0.0)
            evidence_reliability = float(evidence_reliability or 0.0)
            execution_reliability = float(execution_reliability or 0.0)
            execution_cost_estimate = float(execution_cost_estimate or 0.0)
            analytical_state, paper_eligible = _analytical_state(
                str(opportunity_grade),
                str(evidence_grade),
                str(tradability_grade),
                str(risk_grade),
                forecast_reliability,
            )
            policy_blocked = ctx.overall_status != 'healthy' or ctx.freshness_status != 'healthy'
            policy_reason = None if not policy_blocked else f"system={ctx.overall_status or 'unknown'}, freshness={ctx.freshness_status or 'unknown'}"
            final_state = 'blocked' if policy_blocked else analytical_state
            state_json = {
                'Opportunity Grade': opportunity_grade,
                'Evidence Grade': evidence_grade,
                'Tradability Grade': tradability_grade,
                'Risk Containment Grade': risk_grade,
                'forecast_reliability': forecast_reliability,
                'evidence_reliability': evidence_reliability,
                'execution_reliability': execution_reliability,
                'capacity_band': capacity_band,
                'execution_cost_estimate': execution_cost_estimate,
                'grade_percentile': float(grade_percentile or 0.0),
                'policy_blocked': policy_blocked,
                'policy_reason': policy_reason,
            }
            payload.append((
                ctx.cycle_id,
                ticker,
                VERSION,
                analytical_state,
                final_state,
                paper_eligible,
                policy_blocked,
                policy_reason,
                json.dumps(state_json, default=str),
                now,
            ))
            if len(preview) < 10:
                preview.append({
                    'ticker': ticker,
                    'analytical_state': analytical_state,
                    'final_state': final_state,
                    'paper_eligible': paper_eligible,
                    'policy_blocked': policy_blocked,
                })

        with conn.cursor() as cur:
            cur.execute('DELETE FROM decision_states_v2 WHERE cycle_id = %s AND grade_version = %s', (ctx.cycle_id, VERSION))
            from psycopg2.extras import execute_values
            execute_values(cur, 'INSERT INTO decision_states_v2 (cycle_id, ticker, grade_version, analytical_state, final_state, paper_eligible, policy_blocked, policy_reason, state_json, created_at) VALUES %s', payload)

    return {
        'ok': True,
        'cycle_id': ctx.cycle_id,
        'grade_version': VERSION,
        'row_count': len(payload),
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_decision_states()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_decision_states',
            dataset_name='decision_states_v2',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result['row_count'],
            rows_upserted=result['row_count'],
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_decision_states',
            dataset_name='decision_states_v2',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_decision_states',
            stage='build_decision_states',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
