from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class BrokerOrder:
    ticker: str
    side: str
    qty: float
    limit_price: float | None = None

class BrokerInterface:
    name = 'abstract'

    def stage_order(self, order: BrokerOrder) -> dict:
        return {'ok': True, 'broker': self.name, 'staged': True, 'order': order.__dict__}
