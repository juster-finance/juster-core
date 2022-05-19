from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClaimKey:
    event_id: int
    position_id: int

    @classmethod
    def from_tuple(cls, tpl: tuple[int, int]) -> ClaimKey:
        return cls(
            event_id=tpl[0],
            position_id=tpl[1]
        )

    @classmethod
    def from_dict(cls, dct: dict[str, int]) -> ClaimKey:
        return cls(
            event_id=dct['eventId'],
            position_id=dct['positionId']
        )

    def __hash__(self):
        # TODO: this is probably not very good way of hashing, check this out
        return hash(f'{self.event_id}:{self.position_id}')

