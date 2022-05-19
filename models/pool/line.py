from __future__ import annotations

from dataclasses import dataclass

from models.pool.types import AnyStorage


@dataclass
class Line:
    measure_period: int
    bets_period: int
    last_bets_close_time: int
    max_events: int
    is_paused: bool
    min_betting_period: int

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Line:
        return cls(
            measure_period=storage['measurePeriod'],
            bets_period=storage['betsPeriod'],
            last_bets_close_time=storage['lastBetsCloseTime'],
            max_events=storage['maxEvents'],
            is_paused=storage['isPaused'],
            min_betting_period=storage['minBettingPeriod'],
        )

    def update_last_bets_close_time(self, now: int) -> None:
        periods = (now - self.last_bets_close_time) // self.bets_period + 1
        if now < self.last_bets_close_time:
            periods = 1

        self.last_bets_close_time += self.bets_period * periods

        # late event case:
        time_to_event = self.last_bets_close_time - now
        assert time_to_event >= 0
        if time_to_event < self.min_betting_period:
            self.last_bets_close_time += self.bets_period

    def calc_duration(self, now: int) -> int:
        return self.measure_period + self.last_bets_close_time - now
