from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class OrderRequest:
    ticker: str
    side: str
    action: str
    count: int
    price: int
    client_order_id: str = field(default_factory=lambda: str(uuid4()))
    order_type: str | None = None
    expiration_ts: int | None = None
    time_in_force: str | None = None
    post_only: bool = False
    sell_position_floor: int | None = None
    buy_max_cost: int | None = None
    subaccount: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ticker": self.ticker,
            "action": self.action,
            "count": self.count,
            "client_order_id": self.client_order_id,
            "side": self.side,
        }

        if self.side == "yes":
            payload["yes_price"] = self.price
        else:
            payload["no_price"] = self.price

        if self.expiration_ts is not None:
            payload["expiration_ts"] = self.expiration_ts
        if self.order_type is not None:
            payload["type"] = self.order_type
        if self.time_in_force is not None:
            payload["time_in_force"] = self.time_in_force
        if self.post_only:
            payload["post_only"] = True
        if self.sell_position_floor is not None:
            payload["sell_position_floor"] = self.sell_position_floor
        if self.buy_max_cost is not None:
            payload["buy_max_cost"] = self.buy_max_cost
        if self.subaccount is not None:
            payload["subaccount"] = self.subaccount
        return payload
