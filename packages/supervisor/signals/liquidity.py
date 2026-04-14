from __future__ import annotations

from typing import Any

from packages.supervisor.signals.common import expiry_for, normalize_family_rows

BUCKET_BASE = {
    'high': 5.0,
    'medium': 2.5,
    'low': -1.5,
    'unknown': -3.0,
}


def build_liquidity_signals(context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker_row in context.ticker_rows:
        bucket = str(ticker_row.get('liquidity_bucket') or 'unknown')
        turnover = float(ticker_row.get('turnover_last') or 0.0)
        volume = float(ticker_row.get('volume_last') or 0.0)
        turnover_component = min(turnover / 25_000_000_000.0, 4.0)
        volume_component = min(volume / 500_000.0, 2.0)
        raw = BUCKET_BASE.get(bucket, -3.0) + turnover_component + volume_component
        confidence = 0.30 if bucket == 'unknown' else 0.82
        rows.append(
            {
                'cycle_id': context.cycle_id,
                'ticker': ticker_row['ticker'],
                'signal_family': 'liquidity',
                'score_raw': round(raw, 6),
                'confidence': confidence,
                'horizon': 'execution_1d',
                'expires_at': expiry_for(context.created_at, 8),
                'blocking_flag': bucket == 'unknown',
                'reason_json': {
                    'liquidity_bucket': bucket,
                    'turnover_last': turnover,
                    'volume_last': volume,
                },
                'components': [
                    {'component_name': 'bucket_base', 'component_value': BUCKET_BASE.get(bucket, -3.0), 'component_weight': 1.0, 'component_note': bucket},
                    {'component_name': 'turnover_component', 'component_value': turnover_component, 'component_weight': 1.0, 'component_note': 'Scaled turnover support'},
                    {'component_name': 'volume_component', 'component_value': volume_component, 'component_weight': 1.0, 'component_note': 'Scaled volume support'},
                ],
                'created_at': context.created_at,
            }
        )
    return normalize_family_rows(rows)
