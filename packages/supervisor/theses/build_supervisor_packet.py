from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2.extras

from packages.supervisor.snapshots.common import to_jsonable

MAX_PACKET_CANDIDATES = 12


@dataclass(frozen=True)
class SupervisorPacketContext:
    cycle: dict[str, Any]
    regime: dict[str, Any] | None
    health: dict[str, Any] | None
    candidates: list[dict[str, Any]]


def load_latest_phase4_context(conn) -> SupervisorPacketContext:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            '''
            SELECT cycle_id, source_health_snapshot_id, overall_status, freshness_status,
                   frontier_status, universe_count, regime_code, notes_json, created_at
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

        health = None
        if cycle.get('source_health_snapshot_id'):
            cur.execute(
                '''
                SELECT snapshot_id, cycle_id, overall_status, freshness_status, created_at, notes_json
                FROM system_health_snapshots
                WHERE snapshot_id = %s
                LIMIT 1
                ''',
                (cycle['source_health_snapshot_id'],),
            )
            health = cur.fetchone()

        cur.execute(
            '''
            SELECT c.cycle_id, c.ticker, c.total_score, c.total_confidence, c.ranking_bucket,
                   c.blocking_flag, c.ranking_reason_json,
                   t.exchange, t.sector, t.price_last, t.ret_1d, t.ret_5d, t.ret_20d,
                   t.watchlist_score, t.trend_state, t.momentum_state, t.liquidity_bucket,
                   t.snapshot_json,
                   t.snapshot_json->>'industry_name' AS industry_name,
                   t.snapshot_json->>'icb_code' AS icb_code,
                   t.snapshot_json->>'industry_code' AS industry_code,
                   t.snapshot_json->>'classification_source' AS classification_source
            FROM candidate_rankings c
            JOIN ticker_snapshots t
              ON t.cycle_id = c.cycle_id AND t.ticker = c.ticker
            WHERE c.cycle_id = %s
            ORDER BY c.blocking_flag ASC, c.total_score DESC, c.total_confidence DESC, c.ticker ASC
            LIMIT %s
            ''',
            (cycle['cycle_id'], MAX_PACKET_CANDIDATES),
        )
        candidates = [dict(row) for row in cur.fetchall()]

        for candidate in candidates:
            cur.execute(
                '''
                SELECT signal_family, score_raw, score_normalized, confidence,
                       horizon, expires_at, blocking_flag, reason_json, created_at
                FROM signal_scores
                WHERE cycle_id = %s AND ticker = %s
                ORDER BY signal_family ASC
                ''',
                (cycle['cycle_id'], candidate['ticker']),
            )
            scores = [dict(row) for row in cur.fetchall()]
            components_map: dict[str, list[dict[str, Any]]] = {}
            cur.execute(
                '''
                SELECT signal_family, component_name, component_value, component_weight, component_note
                FROM signal_components
                WHERE cycle_id = %s AND ticker = %s
                ORDER BY signal_family ASC, component_name ASC
                ''',
                (cycle['cycle_id'], candidate['ticker']),
            )
            for row in cur.fetchall():
                payload = dict(row)
                components_map.setdefault(payload['signal_family'], []).append(payload)
            candidate['signals'] = [
                {
                    **score,
                    'components': components_map.get(score['signal_family'], []),
                }
                for score in scores
            ]

    return SupervisorPacketContext(
        cycle=dict(cycle),
        regime=dict(regime) if regime else None,
        health=dict(health) if health else None,
        candidates=candidates,
    )


def build_supervisor_packet(conn) -> dict[str, Any]:
    context = load_latest_phase4_context(conn)
    packet = {
        'packet_version': 'phase4_v1',
        'cycle': context.cycle,
        'regime': context.regime,
        'health': context.health,
        'candidate_count': len(context.candidates),
        'candidates': context.candidates,
    }
    return to_jsonable(packet)
