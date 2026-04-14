from __future__ import annotations


def compute_unrealized_pnl(*, qty: float, avg_cost: float, market_price: float | None) -> float:
    if market_price is None:
        return 0.0
    return round((market_price - avg_cost) * qty, 6)
