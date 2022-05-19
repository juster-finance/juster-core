from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from models.pool.helpers import quantize
from models.pool.types import AnyStorage


@dataclass
class Event:
    created_counter: int
    shares: Decimal
    total_shares: Decimal
    locked_shares: Decimal
    result: Optional[Decimal]
    provided: Decimal
    precision: Decimal

    @classmethod
    def from_storage(cls, storage: AnyStorage, precision: Decimal) -> Event:
        result = storage['result']
        return cls(
            created_counter=storage['createdCounter'],
            shares=Decimal(storage['shares']),
            total_shares=Decimal(storage['totalShares']),
            locked_shares=Decimal(storage['lockedShares']),
            result=None if result is None else Decimal(result),
            provided=Decimal(storage['provided']),
            precision=precision
        )

    def get_result_for_shares(self, shares: Decimal) -> Decimal:
        result = self.result if self.result is not None else Decimal(0)
        return quantize(
            result
            * shares
            * self.precision
            / self.total_shares
        )

    def get_provided_for_shares(self, shares: Decimal) -> Decimal:
        return quantize(
            self.provided
            * shares
            * self.precision
            / self.total_shares
        )

