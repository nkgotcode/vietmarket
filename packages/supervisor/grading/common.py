from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2.extras

VERSION = 'grading_reset_v1_2026_04_16'
CONFIG = {
    'feature_snapshot': {
        'critical_fields': ['price_last', 'volume_last', 'turnover_last', 'volatility_20d', 'financial_recency_days'],
    },
    'estimate_weights': {
        'edge_ret_5d': 0.20,
        'edge_ret_20d': 0.20,
        'edge_watchlist': 0.20,
        'edge_trend': 0.20,
        'edge_momentum': 0.20,
    },
    'grade_bands': {
        'opportunity': [(0.85, 'A'), (0.70, 'B'), (0.55, 'C'), (0.40, 'D'), (0.0, 'F')],
        'evidence': [(0.85, 'strong'), (0.70, 'good'), (0.50, 'thin'), (0.30, 'fragile'), (0.0, 'invalid')],
        'tradability': [(0.80, 'excellent'), (0.65, 'good'), (0.45, 'borderline'), (0.25, 'poor'), (0.0, 'untradeable')],
        'risk': [(0.75, 'contained'), (0.55, 'acceptable'), (0.35, 'fragile'), (0.0, 'hazardous')],
    },
}


@dataclass(frozen=True)
class CycleContext:
    cycle_id: str
    created_at: datetime
    overall_status: str | None
    freshness_status: str | None
    frontier_status: str | None
    market_regime: str | None
    regime_confidence: float



def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _dict_rows(cur) -> list[dict[str, Any]]:
    return [dict(row) for row in cur.fetchall()]


def latest_cycle_context(conn) -> CycleContext:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT c.cycle_id, c.created_at, c.overall_status, c.freshness_status, c.frontier_status,
                   r.market_regime, r.confidence AS regime_confidence
            FROM market_state_cycles c
            LEFT JOIN market_regime_snapshots r ON r.cycle_id = c.cycle_id
            ORDER BY c.created_at DESC
            LIMIT 1
            '''
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError('no_market_state_cycle')
    return CycleContext(
        cycle_id=row['cycle_id'],
        created_at=row['created_at'],
        overall_status=row.get('overall_status'),
        freshness_status=row.get('freshness_status'),
        frontier_status=row.get('frontier_status'),
        market_regime=row.get('market_regime'),
        regime_confidence=float(row.get('regime_confidence') or 0.0),
    )


def ensure_grade_version(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO grade_versions (grade_version, status, description, semantics_json, config_json, created_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (grade_version) DO UPDATE SET
              status = EXCLUDED.status,
              description = EXCLUDED.description,
              semantics_json = EXCLUDED.semantics_json,
              config_json = EXCLUDED.config_json
            ''',
            (
                VERSION,
                'active',
                'Grading reset foundation for feature snapshots and first-pass estimate persistence',
                json.dumps({
                    'primary_grades': ['Opportunity Grade', 'Evidence Grade', 'Tradability Grade', 'Risk Containment Grade'],
                    'reliability_dimensions': ['Forecast Reliability', 'Evidence Reliability', 'Execution Reliability'],
                }),
                json.dumps(CONFIG),
            ),
        )


def load_ticker_snapshot_inputs(conn, cycle_id: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT ticker,
                   sector,
                   price_last,
                   volume_last,
                   turnover_last,
                   ret_1d,
                   ret_5d,
                   ret_20d,
                   volatility_20d,
                   financial_recency_days,
                   liquidity_bucket,
                   trend_state,
                   momentum_state,
                   watchlist_score,
                   health_status,
                   corporate_action_flag
            FROM ticker_snapshots
            WHERE cycle_id = %s
            ORDER BY ticker ASC
            ''',
            (cycle_id,),
        )
        return _dict_rows(cur)


def replace_feature_rows(conn, cycle_id: str, rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM feature_snapshots WHERE cycle_id = %s AND grade_version = %s', (cycle_id, VERSION))
        if rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO feature_snapshots (cycle_id, ticker, grade_version, market_regime, regime_confidence, feature_json, feature_quality_json, created_at) VALUES %s',
                rows,
            )


def replace_estimate_rows(conn, cycle_id: str, rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM estimate_snapshots WHERE cycle_id = %s AND grade_version = %s', (cycle_id, VERSION))
        if rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO estimate_snapshots (cycle_id, ticker, grade_version, edge_estimate, downside_estimate, execution_cost_estimate, data_reliability_estimate, estimate_json, created_at) VALUES %s',
                rows,
            )


def replace_grade_rows(
    conn,
    cycle_id: str,
    opportunity_rows: list[tuple],
    evidence_rows: list[tuple],
    tradability_rows: list[tuple],
    risk_rows: list[tuple],
    reliability_rows: list[tuple],
) -> None:
    with conn.cursor() as cur:
        for table in ('opportunity_grades', 'evidence_grades', 'tradability_grades', 'risk_containment_grades', 'reliability_snapshots'):
            cur.execute(f'DELETE FROM {table} WHERE cycle_id = %s AND grade_version = %s', (cycle_id, VERSION))
        if opportunity_rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO opportunity_grades (cycle_id, ticker, grade_version, grade_label, grade_value, grade_percentile, reason_json, created_at) VALUES %s',
                opportunity_rows,
            )
        if evidence_rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO evidence_grades (cycle_id, ticker, grade_version, grade_label, reliability_index, reason_json, created_at) VALUES %s',
                evidence_rows,
            )
        if tradability_rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO tradability_grades (cycle_id, ticker, grade_version, grade_label, tradability_index, execution_cost_estimate, capacity_band, reason_json, created_at) VALUES %s',
                tradability_rows,
            )
        if risk_rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO risk_containment_grades (cycle_id, ticker, grade_version, grade_label, containment_index, reason_json, created_at) VALUES %s',
                risk_rows,
            )
        if reliability_rows:
            psycopg2.extras.execute_values(
                cur,
                'INSERT INTO reliability_snapshots (cycle_id, ticker, grade_version, forecast_reliability, evidence_reliability, execution_reliability, reliability_json, created_at) VALUES %s',
                reliability_rows,
            )
