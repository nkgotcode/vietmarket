from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows


def _recency_component(days: int | None) -> tuple[float, str]:
    if days is None:
        return -4.0, 'missing_financials'
    if days <= 120:
        return 4.0, 'fresh_financials'
    if days <= 240:
        return 2.0, 'acceptable_financials'
    if days <= 365:
        return 0.0, 'aging_financials'
    if days <= 540:
        return -2.0, 'stale_financials'
    return -4.0, 'very_stale_financials'


def build_fundamental_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker_row in context.ticker_rows:
        recency_days = ticker_row.get('financial_recency_days')
        recency_score, recency_note = _recency_component(recency_days)
        volatility = float(ticker_row.get('volatility_20d') or 0.0)
        stability_bonus = max(-1.5, 1.5 - (volatility * 12.0))
        raw = recency_score + stability_bonus
        confidence = 0.30 if recency_days is None else 0.65
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'fundamentals',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'position_20d',
                'expires_at': expiry_for(context.created_at, 72),
                'blocking_flag': False,
                'reason_json': {
                    'financial_recency_days': recency_days,
                    'method': 'canonical_financial_recency_plus_stability',
                },
                'components': [
                    {'component_name': 'financial_recency_score', 'component_value': recency_score, 'component_weight': 1.0, 'component_note': recency_note},
                    {'component_name': 'stability_bonus', 'component_value': stability_bonus, 'component_weight': 1.0, 'component_note': 'Lower volatility improves confidence in stale-or-fresh financial context'},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
