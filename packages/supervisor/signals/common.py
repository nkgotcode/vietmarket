from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import psycopg2.extras

from packages.supervisor.snapshots.common import to_jsonable

DEFAULT_POLICY = {
    'policy_name': 'phase3_default',
    'policy_version': '2026-04-14',
    'weights': {
        'trend': 0.24,
        'momentum': 0.22,
        'catalyst': 0.12,
        'fundamentals': 0.12,
        'liquidity': 0.16,
        'risk': 0.14,
    },
    'blocking_rules': {
        'blocked_health_status': True,
        'max_volatility_20d': 0.18,
    },
    'notes': {
        'description': 'Default deterministic Phase 3 signal-engine aggregation weights',
    },
}


@dataclass(frozen=True)
class SignalBuildContext:
    cycle_id: str
    created_at: datetime
    regime: dict[str, Any] | None
    ticker_rows: list[dict[str, Any]]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def expiry_for(created_at: datetime, hours: int) -> datetime:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(hours=hours)


def load_latest_signal_context(conn) -> SignalBuildContext:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT cycle_id, created_at
            FROM market_state_cycles
            ORDER BY created_at DESC
            LIMIT 1
            '''
        )
        cycle = cur.fetchone()
        if not cycle:
            raise RuntimeError('no_market_state_cycle')

        cur.execute(
            '''
            SELECT cycle_id, market_regime, breadth_state, trend_state, liquidity_state,
                   event_pressure_state, confidence, watchlist_count, reasoning_json, created_at
            FROM market_regime_snapshots
            WHERE cycle_id = %s
            LIMIT 1
            ''',
            (cycle['cycle_id'],),
        )
        regime = cur.fetchone()

        cur.execute(
            '''
            SELECT cycle_id, ticker, exchange, sector, price_last, volume_last, turnover_last,
                   ret_1d, ret_5d, ret_20d, sma20_gap, sma50_gap, ema20_gap, volatility_20d,
                   article_count_24h, corporate_action_flag, financial_recency_days,
                   liquidity_bucket, trend_state, momentum_state, watchlist_score,
                   health_status, snapshot_json, created_at
            FROM ticker_snapshots
            WHERE cycle_id = %s
            ORDER BY ticker ASC
            ''',
            (cycle['cycle_id'],),
        )
        rows = [dict(row) for row in cur.fetchall()]

    return SignalBuildContext(
        cycle_id=cycle['cycle_id'],
        created_at=cycle['created_at'],
        regime=dict(regime) if regime else None,
        ticker_rows=rows,
    )


def normalize_family_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    raw_values = [float(row.get('score_raw') or 0.0) for row in rows]
    min_raw = min(raw_values)
    max_raw = max(raw_values)
    spread = max_raw - min_raw
    for row in rows:
        raw = float(row.get('score_raw') or 0.0)
        normalized = 0.5 if spread <= 1e-9 else (raw - min_raw) / spread
        row['score_normalized'] = round(clamp(normalized), 6)
        row['confidence'] = round(clamp(float(row.get('confidence') or 0.0)), 6)
        row['reason_json'] = to_jsonable(row.get('reason_json') or {})
        row['components'] = [
            {
                'component_name': item['component_name'],
                'component_value': item.get('component_value'),
                'component_weight': item.get('component_weight'),
                'component_note': item.get('component_note'),
            }
            for item in (row.get('components') or [])
        ]
    return rows


def upsert_default_policy(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO signal_policies (
              policy_name, policy_version, policy_scope, weights_json,
              blocking_rules_json, notes_json, created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,now(),now())
            ON CONFLICT (policy_name) DO UPDATE SET
              policy_version = EXCLUDED.policy_version,
              policy_scope = EXCLUDED.policy_scope,
              weights_json = EXCLUDED.weights_json,
              blocking_rules_json = EXCLUDED.blocking_rules_json,
              notes_json = EXCLUDED.notes_json,
              updated_at = now()
            ''',
            (
                DEFAULT_POLICY['policy_name'],
                DEFAULT_POLICY['policy_version'],
                'phase3_signal_engine',
                json.dumps(DEFAULT_POLICY['weights']),
                json.dumps(DEFAULT_POLICY['blocking_rules']),
                json.dumps(DEFAULT_POLICY['notes']),
            ),
        )


def replace_family_scores(conn, *, cycle_id: str, family: str, rows: list[dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            'DELETE FROM signal_components WHERE cycle_id = %s AND signal_family = %s',
            (cycle_id, family),
        )
        cur.execute(
            'DELETE FROM signal_scores WHERE cycle_id = %s AND signal_family = %s',
            (cycle_id, family),
        )
        if rows:
            score_rows = [
                (
                    row['cycle_id'],
                    row['ticker'],
                    row['signal_family'],
                    row['score_raw'],
                    row['score_normalized'],
                    row['confidence'],
                    row['horizon'],
                    row['expires_at'],
                    row['blocking_flag'],
                    json.dumps(to_jsonable(row['reason_json']), default=str),
                    row['created_at'],
                )
                for row in rows
            ]
            psycopg2.extras.execute_values(
                cur,
                '''
                INSERT INTO signal_scores (
                  cycle_id, ticker, signal_family, score_raw, score_normalized,
                  confidence, horizon, expires_at, blocking_flag, reason_json, created_at
                ) VALUES %s
                ''',
                score_rows,
            )
            component_rows = [
                (
                    row['cycle_id'],
                    row['ticker'],
                    row['signal_family'],
                    component['component_name'],
                    component.get('component_value'),
                    component.get('component_weight'),
                    component.get('component_note'),
                    row['created_at'],
                )
                for row in rows
                for component in row.get('components', [])
            ]
            if component_rows:
                psycopg2.extras.execute_values(
                    cur,
                    '''
                    INSERT INTO signal_components (
                      cycle_id, ticker, signal_family, component_name,
                      component_value, component_weight, component_note, created_at
                    ) VALUES %s
                    ''',
                    component_rows,
                )


def load_policy_weights(conn) -> dict[str, float]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            'SELECT weights_json FROM signal_policies WHERE policy_name = %s LIMIT 1',
            (DEFAULT_POLICY['policy_name'],),
        )
        row = cur.fetchone()
    if not row:
        return dict(DEFAULT_POLICY['weights'])
    return {k: float(v) for k, v in (row['weights_json'] or {}).items()}


def load_signal_rows(conn, *, cycle_id: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT cycle_id, ticker, signal_family, score_raw, score_normalized,
                   confidence, horizon, expires_at, blocking_flag, reason_json, created_at
            FROM signal_scores
            WHERE cycle_id = %s
            ORDER BY ticker ASC, signal_family ASC
            ''',
            (cycle_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def replace_candidate_rankings(conn, *, cycle_id: str, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    with conn.cursor() as cur:
        cur.execute('DELETE FROM candidate_rankings WHERE cycle_id = %s', (cycle_id,))
        if not rows:
            return
        payload = [
            (
                row['cycle_id'],
                row['ticker'],
                row['total_score'],
                row['total_confidence'],
                row['ranking_bucket'],
                row['blocking_flag'],
                json.dumps(to_jsonable(row['ranking_reason_json']), default=str),
                row['created_at'],
            )
            for row in rows
        ]
        psycopg2.extras.execute_values(
            cur,
            '''
            INSERT INTO candidate_rankings (
              cycle_id, ticker, total_score, total_confidence,
              ranking_bucket, blocking_flag, ranking_reason_json, created_at
            ) VALUES %s
            ''',
            payload,
        )
