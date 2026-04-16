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
from packages.supervisor.grading.common import CONFIG, VERSION, clamp, latest_cycle_context, replace_grade_rows

PRIMARY_GRADE_NAMES = ['Opportunity Grade', 'Evidence Grade', 'Tradability Grade', 'Risk Containment Grade']
RELIABILITY_NAMES = ['Forecast Reliability', 'Evidence Reliability', 'Execution Reliability']
# Persists into: opportunity_grades, evidence_grades, tradability_grades, risk_containment_grades, reliability_snapshots


def _band_label(value: float, bands: list[tuple[float, str]]) -> str:
    for threshold, label in bands:
        if value >= threshold:
            return label
    return bands[-1][1]


def _capacity_band(liquidity_bucket: str, tradability_index: float) -> str:
    if tradability_index >= 0.80 and liquidity_bucket == 'high':
        return 'large'
    if tradability_index >= 0.55 and liquidity_bucket in {'high', 'medium'}:
        return 'medium'
    if tradability_index >= 0.30:
        return 'small'
    return 'micro'


def build_grades() -> dict:
    with connect() as conn:
        ctx = latest_cycle_context(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT f.ticker,
                       f.feature_json,
                       f.feature_quality_json,
                       e.edge_estimate,
                       e.downside_estimate,
                       e.execution_cost_estimate,
                       e.data_reliability_estimate,
                       e.estimate_json
                FROM feature_snapshots f
                JOIN estimate_snapshots e
                  ON e.cycle_id = f.cycle_id
                 AND e.ticker = f.ticker
                 AND e.grade_version = f.grade_version
                WHERE f.cycle_id = %s AND f.grade_version = %s
                ORDER BY f.ticker ASC
                ''',
                (ctx.cycle_id, VERSION),
            )
            rows = cur.fetchall()

        if not rows:
            raise RuntimeError('no_feature_or_estimate_snapshots_for_latest_cycle')

        total = len(rows)
        opportunity_rows = []
        evidence_rows = []
        tradability_rows = []
        risk_rows = []
        reliability_rows = []
        preview = []
        now = utc_now()
        opportunity_values = [float(row[3] or 0.0) for row in rows]
        sorted_opportunity = sorted(opportunity_values)

        for ticker, feature_json, feature_quality_json, edge_estimate, downside_estimate, execution_cost_estimate, data_reliability_estimate, estimate_json in rows:
            features = dict(feature_json or {})
            quality = dict(feature_quality_json or {})
            estimate_meta = dict(estimate_json or {})
            edge_estimate = float(edge_estimate or 0.0)
            downside_estimate = float(downside_estimate or 0.0)
            execution_cost_estimate = float(execution_cost_estimate or 0.0)
            data_reliability_estimate = float(data_reliability_estimate or 0.0)

            opportunity_grade_value = round(edge_estimate, 6)
            grade_percentile = round(sum(1 for value in sorted_opportunity if value <= edge_estimate) / max(total, 1), 6)
            opportunity_label = _band_label(opportunity_grade_value, CONFIG['grade_bands']['opportunity'])

            evidence_reliability = round(data_reliability_estimate, 6)
            evidence_label = _band_label(evidence_reliability, CONFIG['grade_bands']['evidence'])

            tradability_index = round(clamp(1.0 - execution_cost_estimate), 6)
            liquidity_bucket = str(features.get('liquidity_bucket') or 'unknown')
            tradability_label = _band_label(tradability_index, CONFIG['grade_bands']['tradability'])
            capacity_band = _capacity_band(liquidity_bucket, tradability_index)

            containment_index = round(clamp(1.0 - downside_estimate), 6)
            risk_label = _band_label(containment_index, CONFIG['grade_bands']['risk'])

            forecast_reliability = round(clamp(0.60 * edge_estimate + 0.25 * (1.0 - downside_estimate) + 0.15 * clamp(ctx.regime_confidence)), 6)
            execution_reliability = round(clamp(0.70 * tradability_index + 0.30 * (0.0 if bool(features.get('corporate_action_flag')) else 1.0)), 6)

            opportunity_reason = {
                'display_name': 'Opportunity Grade',
                'edge_estimate': opportunity_grade_value,
                'grade_percentile': grade_percentile,
                'market_regime': ctx.market_regime,
            }
            evidence_reason = {
                'display_name': 'Evidence Grade',
                'Evidence Reliability': evidence_reliability,
                'missing_feature_rate': quality.get('missing_feature_rate'),
                'source_health': quality.get('source_health'),
            }
            tradability_reason = {
                'display_name': 'Tradability Grade',
                'tradability_index': tradability_index,
                'execution_cost_estimate': execution_cost_estimate,
                'liquidity_bucket': liquidity_bucket,
                'capacity_band': capacity_band,
            }
            risk_reason = {
                'display_name': 'Risk Containment Grade',
                'containment_index': containment_index,
                'downside_estimate': downside_estimate,
                'corporate_action_flag': features.get('corporate_action_flag'),
            }
            reliability_json = {
                'Forecast Reliability': forecast_reliability,
                'Evidence Reliability': evidence_reliability,
                'Execution Reliability': execution_reliability,
                'market_regime': ctx.market_regime,
                'estimate_meta': estimate_meta,
            }

            opportunity_rows.append((ctx.cycle_id, ticker, VERSION, opportunity_label, opportunity_grade_value, grade_percentile, json.dumps(opportunity_reason, default=str), now))
            evidence_rows.append((ctx.cycle_id, ticker, VERSION, evidence_label, evidence_reliability, json.dumps(evidence_reason, default=str), now))
            tradability_rows.append((ctx.cycle_id, ticker, VERSION, tradability_label, tradability_index, execution_cost_estimate, capacity_band, json.dumps(tradability_reason, default=str), now))
            risk_rows.append((ctx.cycle_id, ticker, VERSION, risk_label, containment_index, json.dumps(risk_reason, default=str), now))
            reliability_rows.append((ctx.cycle_id, ticker, VERSION, forecast_reliability, evidence_reliability, execution_reliability, json.dumps(reliability_json, default=str), now))

            if len(preview) < 10:
                preview.append({
                    'ticker': ticker,
                    'Opportunity Grade': opportunity_label,
                    'Evidence Grade': evidence_label,
                    'Tradability Grade': tradability_label,
                    'Risk Containment Grade': risk_label,
                    'forecast_reliability': forecast_reliability,
                    'evidence_reliability': evidence_reliability,
                    'execution_reliability': execution_reliability,
                })

        replace_grade_rows(conn, ctx.cycle_id, opportunity_rows, evidence_rows, tradability_rows, risk_rows, reliability_rows)

    return {
        'ok': True,
        'cycle_id': ctx.cycle_id,
        'grade_version': VERSION,
        'primary_grades': PRIMARY_GRADE_NAMES,
        'reliability_dimensions': RELIABILITY_NAMES,
        'row_count': len(opportunity_rows),
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_grades()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_grades',
            dataset_name='opportunity_grades',
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
            job_name='supervisor_build_grades',
            dataset_name='opportunity_grades',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_grades',
            stage='build_grades',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
