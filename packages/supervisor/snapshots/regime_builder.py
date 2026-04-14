from __future__ import annotations

import json
from typing import Any

from packages.supervisor.snapshots.common import MarketContext, to_jsonable


def _pick_breadth_state(breadth_pct: float | None) -> str:
    if breadth_pct is None:
        return 'unknown'
    if breadth_pct >= 0.6:
        return 'strong'
    if breadth_pct <= 0.4:
        return 'weak'
    return 'balanced'


def _pick_trend_state(ticker_rows: list[dict[str, Any]]) -> str:
    if not ticker_rows:
        return 'unknown'
    bullish = sum(1 for row in ticker_rows if row.get('trend_state') == 'bullish')
    bearish = sum(1 for row in ticker_rows if row.get('trend_state') == 'bearish')
    total = len(ticker_rows)
    if bullish / total >= 0.55:
        return 'bullish'
    if bearish / total >= 0.55:
        return 'bearish'
    return 'mixed'


def _pick_liquidity_state(ticker_rows: list[dict[str, Any]]) -> str:
    if not ticker_rows:
        return 'unknown'
    high = sum(1 for row in ticker_rows if row.get('liquidity_bucket') == 'high')
    low = sum(1 for row in ticker_rows if row.get('liquidity_bucket') == 'low')
    total = len(ticker_rows)
    if high / total >= 0.45:
        return 'robust'
    if low / total >= 0.45:
        return 'thin'
    return 'normal'


def _pick_event_pressure_state(ticker_rows: list[dict[str, Any]]) -> str:
    if not ticker_rows:
        return 'unknown'
    flagged = sum(1 for row in ticker_rows if row.get('corporate_action_flag'))
    article_heavy = sum(1 for row in ticker_rows if (row.get('article_count_24h') or 0) >= 2)
    total = len(ticker_rows)
    ratio = max(flagged / total, article_heavy / total)
    if ratio >= 0.2:
        return 'high'
    if ratio >= 0.08:
        return 'moderate'
    return 'low'


def _pick_market_regime(*, health_status: str, frontier_status: str, breadth_state: str, trend_state: str,
                        liquidity_state: str, event_pressure_state: str) -> str:
    if health_status == 'blocked' or frontier_status == 'pipeline_stalled':
        return 'risk_off'
    if breadth_state == 'weak' and trend_state == 'bearish':
        return 'risk_off'
    if breadth_state == 'strong' and trend_state == 'bullish' and liquidity_state == 'robust':
        return 'momentum_expansion'
    if event_pressure_state == 'high':
        return 'event_heavy'
    if breadth_state == 'balanced' and trend_state == 'mixed':
        return 'chop'
    return 'risk_on'


def _confidence(*, market_regime: str, health_status: str, frontier_status: str, breadth_state: str, trend_state: str) -> float:
    score = 0.55
    if market_regime in {'momentum_expansion', 'risk_off'}:
        score += 0.15
    if health_status == 'healthy':
        score += 0.1
    elif health_status == 'blocked':
        score -= 0.1
    if frontier_status == 'fresh':
        score += 0.1
    if breadth_state in {'strong', 'weak'}:
        score += 0.05
    if trend_state in {'bullish', 'bearish'}:
        score += 0.05
    return max(0.25, min(0.95, round(score, 4)))


def build_market_regime(conn, *, cycle_id: str, created_at, context: MarketContext, ticker_rows: list[dict[str, Any]],
                        sector_rows: list[dict[str, Any]]) -> dict[str, Any]:
    breadth_pct = None
    if ticker_rows:
        breadth_pct = sum(1 for row in ticker_rows if (row.get('ret_1d') or 0.0) > 0) / len(ticker_rows)
    breadth_state = _pick_breadth_state(breadth_pct)
    trend_state = _pick_trend_state(ticker_rows)
    liquidity_state = _pick_liquidity_state(ticker_rows)
    event_pressure_state = _pick_event_pressure_state(ticker_rows)
    frontier_status = (context.market_stats.get('candles_frontier_status') or {}).get('value_text') or 'unknown'
    market_regime = _pick_market_regime(
        health_status=context.health.overall_status,
        frontier_status=frontier_status,
        breadth_state=breadth_state,
        trend_state=trend_state,
        liquidity_state=liquidity_state,
        event_pressure_state=event_pressure_state,
    )
    watchlist_count = sum(1 for row in ticker_rows if (row.get('watchlist_score') or 0) >= 2.5)
    confidence = _confidence(
        market_regime=market_regime,
        health_status=context.health.overall_status,
        frontier_status=frontier_status,
        breadth_state=breadth_state,
        trend_state=trend_state,
    )
    reasoning_json = {
        'health': {
            'overall_status': context.health.overall_status,
            'blocking_issue_count': context.health.blocking_issue_count,
            'issue_count': context.health.issue_count,
        },
        'breadth_pct': breadth_pct,
        'trend_mix': {
            'bullish': sum(1 for row in ticker_rows if row.get('trend_state') == 'bullish'),
            'mixed': sum(1 for row in ticker_rows if row.get('trend_state') == 'mixed'),
            'bearish': sum(1 for row in ticker_rows if row.get('trend_state') == 'bearish'),
        },
        'liquidity_mix': {
            'high': sum(1 for row in ticker_rows if row.get('liquidity_bucket') == 'high'),
            'medium': sum(1 for row in ticker_rows if row.get('liquidity_bucket') == 'medium'),
            'low': sum(1 for row in ticker_rows if row.get('liquidity_bucket') == 'low'),
        },
        'event_pressure': {
            'corporate_action_flags': sum(1 for row in ticker_rows if row.get('corporate_action_flag')),
            'article_heavy_names': sum(1 for row in ticker_rows if (row.get('article_count_24h') or 0) >= 2),
        },
        'sector_preview': [
            {
                'sector': row['sector'],
                'breadth_pct': row.get('breadth_pct'),
                'avg_ret_5d': row.get('avg_ret_5d'),
            }
            for row in sorted(sector_rows, key=lambda item: (item.get('breadth_pct') or -1, item.get('avg_ret_5d') or -999), reverse=True)[:5]
        ],
        'frontier_status': frontier_status,
    }
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO market_regime_snapshots (
              cycle_id, market_regime, breadth_state, trend_state, liquidity_state,
              event_pressure_state, confidence, watchlist_count, reasoning_json, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''',
            (
                cycle_id,
                market_regime,
                breadth_state,
                trend_state,
                liquidity_state,
                event_pressure_state,
                confidence,
                watchlist_count,
                json.dumps(to_jsonable(reasoning_json), default=str),
                created_at,
            ),
        )
    return {
        'cycle_id': cycle_id,
        'market_regime': market_regime,
        'breadth_state': breadth_state,
        'trend_state': trend_state,
        'liquidity_state': liquidity_state,
        'event_pressure_state': event_pressure_state,
        'confidence': confidence,
        'watchlist_count': watchlist_count,
        'reasoning_json': reasoning_json,
        'created_at': created_at,
    }
