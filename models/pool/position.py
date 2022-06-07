from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from models.pool.types import AnyStorage


@dataclass
class Position:
    provider: str
    shares: Decimal

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Position:
        return cls(
            provider=storage['provider'],
            shares=Decimal(storage['shares']),
        )

    def remove_shares(self, shares: Decimal):
        self.shares -= shares
        assert self.shares >= 0
