from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from models.pool.helpers import quantize
from models.pool.types import AnyStorage


@dataclass
class Event:
    claimed: Decimal
    result: Optional[Decimal]
    provided: Decimal
    precision: Decimal

    @classmethod
    def from_storage(cls, storage: AnyStorage, precision: Decimal) -> Event:
        result = storage['result']
        return cls(
            claimed=Decimal(storage['claimed']),
            result=None if result is None else Decimal(result),
            provided=Decimal(storage['provided']),
            precision=precision,
        )

    def get_result_for_provided_f(self, provided: Decimal) -> Decimal:
        result = self.result if self.result is not None else Decimal(0)
        return quantize(result * provided * self.precision / self.provided)
