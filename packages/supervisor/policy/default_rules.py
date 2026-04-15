from __future__ import annotations

DEFAULT_RISK_LIMITS = {
    'starting_cash_balance': 1_000_000_000.0,
    'max_new_positions': 5.0,
    'confidence_floor': 0.65,
    'min_liquidity_score': 0.45,
    'max_sector_share': 0.35,
}

DEFAULT_PROMOTION_POLICY = {
    'promotion_policy_version': 'promotion_v1_2026_04_15',
    'paper_trading_enabled': False,
    'thresholds': {
        'decision_score': 70.0,
        'model_confidence': 0.58,
        'evidence_confidence': 0.70,
        'execution_confidence': 0.72,
        'risk_score': 55.0,
        'execution_score': 55.0,
    },
    'notes': {
        'reason': 'paper trading stays disabled until explicit operator approval even if recommendations are paper_eligible',
    },
}
