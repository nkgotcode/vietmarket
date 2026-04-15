from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2.extras

VERSION = 'scoring_v2_2026_04_15'
CONFIG = {
    'alpha_weights': {
        'trend': 0.30,
        'momentum': 0.25,
        'catalyst': 0.15,
        'fundamentals': 0.15,
        'legacy_total_score': 0.15,
    },
    'decision_weights': {
        'alpha': 0.45,
        'quality': 0.20,
        'risk': 0.20,
        'execution': 0.15,
    },
    'paper_thresholds': {
        'decision_score': 70.0,
        'model_confidence': 0.58,
        'evidence_confidence': 0.70,
        'execution_confidence': 0.72,
        'risk_score': 55.0,
        'execution_score': 55.0,
    },
}


@dataclass(frozen=True)
class ScoringInput:
    cycle_id: str
    created_at: datetime
    overall_status: str | None
    freshness_status: str | None
    frontier_status: str | None
    market_regime: str | None
    regime_confidence: float
    rows: list[dict[str, Any]]
    calibration: dict[str, float]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def clamp100(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 4)


def connect_rows(conn, cycle_id: str) -> ScoringInput:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT c.cycle_id, c.created_at, c.overall_status, c.freshness_status, c.frontier_status,
                   r.market_regime, r.confidence AS regime_confidence
            FROM market_state_cycles c
            LEFT JOIN market_regime_snapshots r ON r.cycle_id = c.cycle_id
            WHERE c.cycle_id = %s
            LIMIT 1
            ''',
            (cycle_id,),
        )
        cycle = cur.fetchone()
        if not cycle:
            raise RuntimeError('no_market_state_cycle')

        cur.execute(
            '''
            SELECT ts.ticker,
                   ts.sector,
                   ts.price_last,
                   ts.volume_last,
                   ts.turnover_last,
                   ts.ret_1d,
                   ts.ret_5d,
                   ts.ret_20d,
                   ts.volatility_20d,
                   ts.financial_recency_days,
                   ts.liquidity_bucket,
                   ts.trend_state,
                   ts.momentum_state,
                   ts.watchlist_score,
                   ts.health_status,
                   ts.corporate_action_flag,
                   cr.total_score AS legacy_total_score,
                   cr.total_confidence AS legacy_total_confidence,
                   cr.ranking_bucket AS legacy_bucket,
                   cr.blocking_flag AS legacy_blocking_flag,
                   coalesce(max(case when ss.signal_family = 'trend' then ss.score_normalized end), 0) as trend_score,
                   coalesce(max(case when ss.signal_family = 'momentum' then ss.score_normalized end), 0) as momentum_score,
                   coalesce(max(case when ss.signal_family = 'catalyst' then ss.score_normalized end), 0) as catalyst_score,
                   coalesce(max(case when ss.signal_family = 'fundamentals' then ss.score_normalized end), 0) as fundamentals_score,
                   coalesce(max(case when ss.signal_family = 'liquidity' then ss.score_normalized end), 0) as liquidity_signal_score,
                   coalesce(max(case when ss.signal_family = 'risk' then ss.score_normalized end), 0) as risk_signal_score,
                   coalesce(max(case when ss.signal_family = 'trend' then ss.confidence end), 0) as trend_confidence,
                   coalesce(max(case when ss.signal_family = 'momentum' then ss.confidence end), 0) as momentum_confidence,
                   coalesce(max(case when ss.signal_family = 'catalyst' then ss.confidence end), 0) as catalyst_confidence,
                   coalesce(max(case when ss.signal_family = 'fundamentals' then ss.confidence end), 0) as fundamentals_confidence,
                   coalesce(max(case when ss.signal_family = 'liquidity' then ss.confidence end), 0) as liquidity_confidence,
                   coalesce(max(case when ss.signal_family = 'risk' then ss.confidence end), 0) as risk_confidence
            FROM ticker_snapshots ts
            LEFT JOIN candidate_rankings cr ON cr.cycle_id = ts.cycle_id AND cr.ticker = ts.ticker
            LEFT JOIN signal_scores ss ON ss.cycle_id = ts.cycle_id AND ss.ticker = ts.ticker
            WHERE ts.cycle_id = %s
            GROUP BY ts.ticker, ts.sector, ts.price_last, ts.volume_last, ts.turnover_last, ts.ret_1d,
                     ts.ret_5d, ts.ret_20d, ts.volatility_20d, ts.financial_recency_days, ts.liquidity_bucket,
                     ts.trend_state, ts.momentum_state, ts.watchlist_score, ts.health_status,
                     ts.corporate_action_flag, cr.total_score, cr.total_confidence, cr.ranking_bucket,
                     cr.blocking_flag
            ORDER BY ts.ticker ASC
            ''',
            (cycle_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]

        cur.execute(
            "SELECT metric_name, metric_value FROM calibration_metrics WHERE metric_name IN ('positive_rate_5d','top_bottom_spread_5d','sample_size_5d')"
        )
        calibration = {str(name): float(value) for name, value in cur.fetchall()}

    return ScoringInput(
        cycle_id=cycle['cycle_id'],
        created_at=cycle['created_at'],
        overall_status=cycle.get('overall_status'),
        freshness_status=cycle.get('freshness_status'),
        frontier_status=cycle.get('frontier_status'),
        market_regime=cycle.get('market_regime'),
        regime_confidence=float(cycle.get('regime_confidence') or 0.0),
        rows=rows,
        calibration=calibration,
    )


def ensure_score_version(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO score_versions (score_version, status, description, config_json, created_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (score_version) DO UPDATE SET
              status = EXCLUDED.status,
              description = EXCLUDED.description,
              config_json = EXCLUDED.config_json
            ''',
            (VERSION, 'active', 'Explicit alpha/quality/risk/execution/decion scoring side-by-side v2', json.dumps(CONFIG)),
        )


def replace_v2_rows(conn, cycle_id: str, alpha_rows: list[tuple], quality_rows: list[tuple], risk_rows: list[tuple], execution_rows: list[tuple], decision_rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        for table in ('alpha_scores', 'quality_scores', 'risk_scores_v2', 'execution_scores', 'decision_scores'):
            cur.execute(f'DELETE FROM {table} WHERE cycle_id = %s AND score_version = %s', (cycle_id, VERSION))
        if alpha_rows:
            psycopg2.extras.execute_values(cur, 'INSERT INTO alpha_scores (cycle_id, ticker, score_version, alpha_score, model_confidence, reason_json, created_at) VALUES %s', alpha_rows)
        if quality_rows:
            psycopg2.extras.execute_values(cur, 'INSERT INTO quality_scores (cycle_id, ticker, score_version, quality_score, evidence_confidence, reason_json, created_at) VALUES %s', quality_rows)
        if risk_rows:
            psycopg2.extras.execute_values(cur, 'INSERT INTO risk_scores_v2 (cycle_id, ticker, score_version, risk_score, block_flag, reason_json, created_at) VALUES %s', risk_rows)
        if execution_rows:
            psycopg2.extras.execute_values(cur, 'INSERT INTO execution_scores (cycle_id, ticker, score_version, execution_score, execution_confidence, reason_json, created_at) VALUES %s', execution_rows)
        if decision_rows:
            psycopg2.extras.execute_values(cur, 'INSERT INTO decision_scores (cycle_id, ticker, score_version, alpha_score, quality_score, risk_score, execution_score, decision_score, model_confidence, evidence_confidence, execution_confidence, recommended_state, paper_eligible, block_reason_json, score_json, created_at) VALUES %s', decision_rows)
