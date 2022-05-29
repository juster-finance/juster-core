from __future__ import annotations

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class ClaimKey:
    event_id: int
    position_id: int

    @classmethod
    def from_tuple(cls, tpl: tuple[int, int]) -> ClaimKey:
        return cls(event_id=tpl[0], position_id=tpl[1])

    @classmethod
    def from_dict(cls, dct: dict[str, int]) -> ClaimKey:
        return cls(event_id=dct['eventId'], position_id=dct['positionId'])
