from __future__ import annotations

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class ClaimKey:
    event_id: int
    provider: str

    @classmethod
    def from_tuple(cls, tpl: tuple[int, str]) -> ClaimKey:
        return cls(event_id=tpl[0], provider=tpl[1])

    @classmethod
    def from_dict(cls, dct: dict[str, str]) -> ClaimKey:
        return cls(event_id=dct['eventId'], provider=dct['provider'])
