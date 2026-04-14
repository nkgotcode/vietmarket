from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows


def build_catalyst_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    event_pressure = ((context.regime or {}).get('event_pressure_state') or 'unknown') if context.regime else 'unknown'
    regime_penalty = -0.5 if event_pressure == 'high' else 0.0
    for ticker_row in context.ticker_rows:
        articles = int(ticker_row.get('article_count_24h') or 0)
        corp_action = bool(ticker_row.get('corporate_action_flag'))
        raw = min(articles, 10) * 0.8
        raw += 1.2 if corp_action else 0.0
        raw += regime_penalty
        confidence = 0.35 + min(articles, 5) * 0.07
        if corp_action:
            confidence += 0.15
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'catalyst',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'event_1d',
                'expires_at': expiry_for(context.created_at, 12),
                'blocking_flag': False,
                'reason_json': {
                    'article_count_24h': articles,
                    'corporate_action_flag': corp_action,
                    'event_pressure_state': event_pressure,
                },
                'components': [
                    {'component_name': 'article_count_24h', 'component_value': float(articles), 'component_weight': 0.8, 'component_note': 'Recent news volume'},
                    {'component_name': 'corporate_action_bonus', 'component_value': 1.2 if corp_action else 0.0, 'component_weight': 1.0, 'component_note': 'Recent corporate action presence'},
                    {'component_name': 'event_pressure_penalty', 'component_value': regime_penalty, 'component_weight': 1.0, 'component_note': event_pressure},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
