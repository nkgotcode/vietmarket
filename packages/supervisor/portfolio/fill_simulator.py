from __future__ import annotations

from typing import Any


def simulate_fill_price(reference_price: float | None) -> float:
    return float(reference_price or 0.0)


def simulate_fill_qty(target_qty: float) -> float:
    return float(target_qty)
