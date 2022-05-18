from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from models.pool.types import AnyStorage


@dataclass
class Entry:
    provider: str
    amount: Decimal
    accept_after: int

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Entry:
        return cls(
            provider=storage['provider'],
            amount=Decimal(storage['amount']),
            accept_after=int(storage['acceptAfter'])
        )


