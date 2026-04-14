from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows

STATE_BONUS = {
    'strong': 2.0,
    'improving': 1.0,
    'neutral': 0.0,
    'slipping': -1.0,
    'weak': -2.0,
}


def build_momentum_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker_row in context.ticker_rows:
        ret_1d = float(ticker_row.get('ret_1d') or 0.0)
        ret_5d = float(ticker_row.get('ret_5d') or 0.0)
        ret_20d = float(ticker_row.get('ret_20d') or 0.0)
        momentum_state = str(ticker_row.get('momentum_state') or 'neutral')
        raw = (ret_1d * 100.0 * 0.20) + (ret_5d * 100.0 * 0.50) + (ret_20d * 100.0 * 0.30) + STATE_BONUS.get(momentum_state, 0.0)
        confidence = 0.50
        for field in ('ret_1d', 'ret_5d', 'ret_20d'):
            if ticker_row.get(field) is not None:
                confidence += 0.10
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'momentum',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'swing_3d',
                'expires_at': expiry_for(context.created_at, 16),
                'blocking_flag': False,
                'reason_json': {
                    'momentum_state': momentum_state,
                    'watchlist_score': ticker_row.get('watchlist_score'),
                },
                'components': [
                    {'component_name': 'ret_1d', 'component_value': ret_1d, 'component_weight': 0.20, 'component_note': '1-day return'},
                    {'component_name': 'ret_5d', 'component_value': ret_5d, 'component_weight': 0.50, 'component_note': '5-day return'},
                    {'component_name': 'ret_20d', 'component_value': ret_20d, 'component_weight': 0.30, 'component_note': '20-day return'},
                    {'component_name': 'momentum_state_bonus', 'component_value': STATE_BONUS.get(momentum_state, 0.0), 'component_weight': 1.0, 'component_note': momentum_state},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
