from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from models.pool.types import AnyStorage


@dataclass
class Claim:
    shares: Decimal
    provider: str

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Claim:
        return cls(
            shares=Decimal(storage['shares']),
            provider=storage['provider']
        )

