from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from models.pool.types import AnyStorage


@dataclass
class DurationPoints:
    amount: Decimal
    update_level: int

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> DurationPoints:
        return cls(
            amount=Decimal(storage['amount']),
            update_level=int(storage['updateLevel']),
        )
