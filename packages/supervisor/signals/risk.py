from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows


def build_risk_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker_row in context.ticker_rows:
        volatility = float(ticker_row.get('volatility_20d') or 0.0)
        health_status = str(ticker_row.get('health_status') or 'unknown')
        corp_action = bool(ticker_row.get('corporate_action_flag'))
        bucket = str(ticker_row.get('liquidity_bucket') or 'unknown')
        safety_base = 6.0
        volatility_penalty = min(volatility * 40.0, 8.0)
        health_penalty = 6.0 if health_status == 'blocked' else (2.0 if health_status == 'degraded' else 0.0)
        corp_action_penalty = 1.0 if corp_action else 0.0
        liquidity_penalty = 3.0 if bucket == 'unknown' else (1.5 if bucket == 'low' else 0.0)
        raw = safety_base - volatility_penalty - health_penalty - corp_action_penalty - liquidity_penalty
        blocking = health_status == 'blocked' or volatility >= 0.18
        confidence = 0.75 if ticker_row.get('volatility_20d') is not None else 0.40
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'risk',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'risk_1d',
                'expires_at': expiry_for(context.created_at, 8),
                'blocking_flag': blocking,
                'reason_json': {
                    'volatility_20d': volatility,
                    'health_status': health_status,
                    'corporate_action_flag': corp_action,
                    'liquidity_bucket': bucket,
                },
                'components': [
                    {'component_name': 'safety_base', 'component_value': safety_base, 'component_weight': 1.0, 'component_note': 'Base safety score'},
                    {'component_name': 'volatility_penalty', 'component_value': -volatility_penalty, 'component_weight': 1.0, 'component_note': '20d volatility penalty'},
                    {'component_name': 'health_penalty', 'component_value': -health_penalty, 'component_weight': 1.0, 'component_note': health_status},
                    {'component_name': 'corporate_action_penalty', 'component_value': -corp_action_penalty, 'component_weight': 1.0, 'component_note': 'Recent action can distort short-term execution'},
                    {'component_name': 'liquidity_penalty', 'component_value': -liquidity_penalty, 'component_weight': 1.0, 'component_note': bucket},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
