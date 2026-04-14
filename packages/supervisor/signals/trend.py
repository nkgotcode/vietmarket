from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows

STATE_BONUS = {
    'bullish': 2.0,
    'mixed': 0.0,
    'bearish': -2.0,
    'unknown': -1.0,
}


def build_trend_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker_row in context.ticker_rows:
        sma20_gap = float(ticker_row.get('sma20_gap') or 0.0)
        sma50_gap = float(ticker_row.get('sma50_gap') or 0.0)
        ema20_gap = float(ticker_row.get('ema20_gap') or 0.0)
        trend_state = str(ticker_row.get('trend_state') or 'unknown')
        raw = (sma20_gap * 100.0 * 0.42) + (sma50_gap * 100.0 * 0.38) + (ema20_gap * 100.0 * 0.20) + STATE_BONUS.get(trend_state, 0.0)
        confidence = 0.55
        if ticker_row.get('sma20_gap') is not None and ticker_row.get('sma50_gap') is not None:
            confidence += 0.20
        if ticker_row.get('ema20_gap') is not None:
            confidence += 0.10
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'trend',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'swing_5d',
                'expires_at': expiry_for(context.created_at, 24),
                'blocking_flag': False,
                'reason_json': {
                    'trend_state': trend_state,
                    'sector': ticker_row.get('sector'),
                    'components_considered': ['sma20_gap', 'sma50_gap', 'ema20_gap'],
                },
                'components': [
                    {'component_name': 'sma20_gap', 'component_value': sma20_gap, 'component_weight': 0.42, 'component_note': 'Price vs SMA20'},
                    {'component_name': 'sma50_gap', 'component_value': sma50_gap, 'component_weight': 0.38, 'component_note': 'Price vs SMA50'},
                    {'component_name': 'ema20_gap', 'component_value': ema20_gap, 'component_weight': 0.20, 'component_note': 'Price vs EMA20'},
                    {'component_name': 'trend_state_bonus', 'component_value': STATE_BONUS.get(trend_state, 0.0), 'component_weight': 1.0, 'component_note': trend_state},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
