from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Type

from models.pool.claim_key import ClaimKey
from models.pool.entry import Entry
from models.pool.event import Event
from models.pool.duration_points import DurationPoints
from models.pool.helpers import quantize
from models.pool.helpers import quantize_up
from models.pool.line import Line
from models.pool.types import AnyStorage


@dataclass
class PoolModel:
    """Model that emulates simplified Pool case with one event line"""

    # TODO: add f postfix to all high precision values
    active_events: list[int] = field(default_factory=list)
    shares: dict[str, Decimal] = field(default_factory=dict)
    total_shares: Decimal = Decimal(0)
    events: dict[int, Event] = field(default_factory=dict)
    claims: dict[ClaimKey, Decimal] = field(default_factory=dict)
    entries: dict[int, Entry] = field(default_factory=dict)
    max_events: int = 0
    precision: Decimal = Decimal(10**6)
    balance: Decimal = Decimal(0)
    next_entry_id: int = 0
    next_position_id: int = 0
    entry_lock_period: int = 0
    now: int = 0
    active_liquidity_f: Decimal = Decimal(0)
    withdrawable_liquidity_f: Decimal = Decimal(0)
    lines: dict[int, Line] = field(default_factory=dict)
    next_line_id: int = 0
    duration_points: dict[str, DurationPoints] = field(default_factory=dict)
    total_duration_points: Decimal = Decimal(0)
    level: int = 0

    @classmethod
    def from_storage(
        cls: Type[PoolModel],
        storage: AnyStorage,
        balance: Decimal = Decimal(0),
        now: int = 0,
        level: int = 0,
    ) -> PoolModel:
        def convert(cls: Any, items: AnyStorage):
            return {
                index: cls.from_storage(item_storage)
                for index, item_storage in items.items()
            }

        precision = Decimal(storage['precision'])

        claims = {
            ClaimKey.from_tuple(index): Decimal(claim)
            for index, claim in storage['claims'].items()
        }

        events = {
            index: Event.from_storage(event, precision)
            for index, event in storage['events'].items()
        }

        shares = {
            address: Decimal(share)
            for address, share in storage['shares'].items()
        }

        return cls(
            active_events=list(storage['activeEvents'].keys()),
            shares=shares,
            total_shares=Decimal(storage['totalShares']),
            events=events,
            entries=convert(Entry, storage['entries']),
            claims=claims,
            max_events=storage['maxEvents'],
            precision=precision,
            balance=balance,
            next_entry_id=storage['nextEntryId'],
            entry_lock_period=storage['entryLockPeriod'],
            now=now,
            active_liquidity_f=Decimal(storage['activeLiquidityF']),
            withdrawable_liquidity_f=Decimal(
                storage['withdrawableLiquidityF']
            ),
            lines=convert(Line, storage['lines']),
            next_line_id=storage['nextLineId'],
            duration_points=convert(DurationPoints, storage['durationPoints']),
            total_duration_points=Decimal(storage['totalDurationPoints']),
            level=level,
        )

    def trigger_pause_line(self, line_id: int) -> bool:
        line = self.lines[line_id]
        diff = line.max_events
        self.max_events += diff if line.is_paused else -diff
        line.is_paused = not line.is_paused
        return line.is_paused

    def add_line(
        self,
        measure_period: int,
        bets_period: int,
        last_bets_close_time: int,
        max_events: int,
        is_paused: bool,
        min_betting_period: int,
    ) -> int:
        line_id = self.next_line_id
        self.lines[line_id] = Line(
            measure_period=measure_period,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time,
            max_events=max_events,
            is_paused=is_paused,
            min_betting_period=min_betting_period,
        )
        self.next_line_id += 1
        self.max_events += 0 if is_paused else max_events
        return line_id

    def calc_entry_liquidity_f(self):
        return quantize(
            sum(
                entry.amount * self.precision
                for entry in self.entries.values()
            )
        )

    def calc_free_liquidity_f(self):
        return (
            self.balance * self.precision
            - self.withdrawable_liquidity_f
            - self.calc_entry_liquidity_f()
        )

    def calc_total_liquidity_f(self):
        return self.calc_free_liquidity_f() + self.active_liquidity_f

    def calc_deposit_shares(self, amount: Decimal):
        is_first_deposit = self.total_shares == 0
        if is_first_deposit:
            return amount

        return quantize(
            amount
            * self.precision
            * self.total_shares
            / self.calc_total_liquidity_f()
        )

    def calc_withdraw_payouts_f(
        self, claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts_f: dict[str, Decimal] = {}
        for claim_key in claim_keys:
            claim_amount = self.claims[claim_key]
            event = self.events[claim_key.event_id]
            payout_f = payouts_f.get(claim_key.provider, Decimal(0))
            payout_f += event.get_result_for_provided_f(claim_amount)
            payouts_f[claim_key.provider] = payout_f

        return payouts_f

    def calc_withdraw_payouts(
        self, claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts_f = self.calc_withdraw_payouts_f(claim_keys)
        return {
            address: quantize(payout_f / self.precision)
            for address, payout_f in payouts_f.items()
        }

    def update_duration_points(self, provider: str) -> None:
        init_points = DurationPoints(amount=0, update_level=self.level)
        last_points = self.duration_points.get(provider, init_points)

        shares_amount = self.shares.get(provider, Decimal(0))
        duration = self.level - last_points.update_level

        added_amount = shares_amount * duration
        self.duration_points[provider] = DurationPoints(
            amount=last_points.amount + added_amount,
            update_level=self.level,
        )
        self.total_duration_points += added_amount

    def deposit_liquidity(self, user: str, amount: Decimal) -> int:
        accept_after = self.now + self.entry_lock_period
        entry = Entry(user, amount, accept_after)
        entry_id = self.next_entry_id
        self.entries[entry_id] = entry
        self.next_entry_id += 1
        self.balance += amount

        return entry_id

    def approve_entry(self, entry_id: int) -> int:
        entry = self.entries[entry_id]
        self.update_duration_points(entry.provider)
        new_shares = self.calc_deposit_shares(entry.amount)
        existed_shares = self.shares.get(entry.provider, Decimal(0))
        self.shares[entry.provider] = existed_shares + new_shares
        self.total_shares += new_shares
        self.entries.pop(entry_id)
        return entry.provider

    def cancel_entry(self, entry_id: int) -> None:
        entry = self.entries[entry_id]
        self.entries.pop(entry_id)
        self.balance -= entry.amount

    def add_claim_shares(
        self, event_id: int, provider: str, shares: Decimal
    ) -> None:
        claim_key = ClaimKey(event_id, provider)
        claim_amount = self.claims.get(claim_key, Decimal(0))
        event = self.events[event_id]

        # TODO: maube it is better to have here withdrawn_fraction_f:
        left_provided = event.provided - event.claimed

        event_claimed_f = quantize(
            shares * self.precision * left_provided / self.total_shares
        )
        event_claimed = quantize_up(event_claimed_f / self.precision)
        self.claims[claim_key] = claim_amount + event_claimed

        event.claimed += event_claimed
        self.events[event_id] = event

        # TODO: consider removing high precision from active liquidity:
        self.active_liquidity_f -= event_claimed * self.precision

    def calc_claim_payout(self, shares: Decimal) -> Decimal:
        free_liquidity_f = self.calc_free_liquidity_f()
        return quantize(
            free_liquidity_f * shares / self.total_shares / self.precision
        )

    def claim_liquidity(self, provider: str, shares: Decimal) -> Decimal:
        if shares == 0:
            return Decimal(0)

        self.update_duration_points(provider)
        payout = self.calc_claim_payout(shares)
        self.shares[provider] -= shares

        for event_id in self.active_events:
            self.add_claim_shares(event_id, provider, shares)

        self.total_shares -= shares
        assert self.total_shares >= Decimal(0)

        self.balance -= payout
        assert self.balance >= Decimal(0)

        return payout

    def withdraw_claims(
        self, claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts_f = self.calc_withdraw_payouts_f(claim_keys)
        payouts = self.calc_withdraw_payouts(claim_keys)
        [self.claims.pop(key) for key in claim_keys]
        self.withdrawable_liquidity_f -= sum(payouts_f.values())
        self.balance -= sum(payouts.values())
        return payouts

    def pay_reward(self, event_id: int, amount: Decimal) -> None:
        event = self.events[event_id]
        event.result = amount

        locked_amount_f = event.get_result_for_provided_f(event.claimed)
        self.withdrawable_liquidity_f += locked_amount_f

        left_amount = event.provided - event.claimed
        self.active_liquidity_f -= left_amount * self.precision
        assert self.active_liquidity_f >= Decimal(0)

        self.active_events.remove(event_id)
        self.balance += amount

    def calc_next_event_liquidity(self) -> Decimal:
        max_liquidity_f = quantize(
            self.calc_total_liquidity_f() / self.max_events
        )
        liquidity_f = min(max_liquidity_f, self.calc_free_liquidity_f())
        return quantize(liquidity_f / self.precision)

    def create_event(self, line_id: int, next_event_id: int) -> int:
        assert not next_event_id in self.events
        provided_amount = self.calc_next_event_liquidity()
        active_fraction_f = quantize_up(self.precision / self.max_events)

        self.events[next_event_id] = Event(
            claimed=Decimal(0),
            result=None,
            provided=provided_amount,
            precision=self.precision,
        )

        self.active_liquidity_f += provided_amount * self.precision
        line = self.lines[line_id]
        line.update_last_bets_close_time(self.now)
        duration = line.calc_duration(self.now)
        self.balance -= provided_amount
        self.active_events.append(next_event_id)
        assert self.balance >= Decimal(0)

        return next_event_id

    def default(self, amount: Decimal) -> None:
        self.balance += amount

    def diff_with(self, other: PoolModel) -> list[str]:
        """Returns attributes that different with other"""
        return [
            attr_name
            for attr_name, attr_value in self.__dict__.items()
            if attr_value != getattr(other, attr_name)
        ]
