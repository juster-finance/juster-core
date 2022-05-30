from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Type

from models.pool.claim import Claim
from models.pool.claim_key import ClaimKey
from models.pool.entry import Entry
from models.pool.event import Event
from models.pool.helpers import quantize
from models.pool.helpers import quantize_up
from models.pool.line import Line
from models.pool.position import Position
from models.pool.types import AnyStorage


@dataclass
class PoolModel:
    """Model that emulates simplified Pool case with one event line"""

    # TODO: add f postfix to all high precision values
    active_events: list[int] = field(default_factory=list)
    positions: dict[int, Position] = field(default_factory=dict)
    total_shares: Decimal = Decimal(0)
    events: dict[int, Event] = field(default_factory=dict)
    claims: dict[ClaimKey, Claim] = field(default_factory=dict)
    entries: dict[int, Entry] = field(default_factory=dict)
    max_events: int = 0
    counter: int = 0
    precision: Decimal = Decimal(10**6)
    liquidity_units: Decimal = Decimal(0)
    balance: Decimal = Decimal(0)
    next_entry_id: int = 0
    next_position_id: int = 0
    entry_lock_period: int = 0
    now: int = 0
    active_liquidity_f: Decimal = Decimal(0)
    withdrawable_liquidity_f: Decimal = Decimal(0)
    lines: dict[int, Line] = field(default_factory=dict)
    next_line_id: int = 0

    @classmethod
    def from_storage(
        cls: Type[PoolModel],
        storage: AnyStorage,
        balance: Decimal = Decimal(0),
        now: int = 0,
    ) -> PoolModel:
        def convert(cls: Any, items: AnyStorage):
            return {
                index: cls.from_storage(item_storage)
                for index, item_storage in items.items()
            }

        precision = Decimal(storage['precision'])

        claims = {
            ClaimKey.from_tuple(index): Claim.from_storage(claim)
            for index, claim in storage['claims'].items()
        }

        events = {
            index: Event.from_storage(event, precision)
            for index, event in storage['events'].items()
        }

        return cls(
            active_events=list(storage['activeEvents'].keys()),
            positions=convert(Position, storage['positions']),
            total_shares=Decimal(storage['totalShares']),
            events=events,
            entries=convert(Entry, storage['entries']),
            claims=claims,
            max_events=storage['maxEvents'],
            counter=storage['counter'],
            precision=precision,
            liquidity_units=Decimal(storage['liquidityUnits']),
            balance=balance,
            next_entry_id=storage['nextEntryId'],
            next_position_id=storage['nextPositionId'],
            entry_lock_period=storage['entryLockPeriod'],
            now=now,
            active_liquidity_f=Decimal(storage['activeLiquidityF']),
            withdrawable_liquidity_f=Decimal(
                storage['withdrawableLiquidityF']
            ),
            lines=convert(Line, storage['lines']),
            next_line_id=storage['nextLineId'],
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
            claim = self.claims[claim_key]
            event = self.events[claim_key.event_id]
            payout_f = payouts_f.get(claim.provider, Decimal(0))
            payout_f += event.get_result_for_shares_f(claim.shares)
            payouts_f[claim.provider] = payout_f

        return payouts_f

    def calc_withdraw_payouts(
        self, claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts_f = self.calc_withdraw_payouts_f(claim_keys)
        return {
            address: quantize(payout_f / self.precision)
            for address, payout_f in payouts_f.items()
        }

    def deposit_liquidity(self, user: str, amount: Decimal) -> int:
        accept_after = self.now + self.entry_lock_period
        entry = Entry(user, amount, accept_after)
        entry_id = self.next_entry_id
        self.entries[entry_id] = entry
        self.next_entry_id += 1
        self.balance += amount

        return entry_id

    def approve_liquidity(self, entry_id: int) -> int:
        entry = self.entries[entry_id]
        position = Position(
            provider=entry.provider,
            shares=self.calc_deposit_shares(entry.amount),
            added_counter=self.counter,
        )
        self.entries.pop(entry_id)

        position_id = self.next_position_id
        self.positions[position_id] = position
        self.next_position_id += 1
        self.total_shares += position.shares
        self.counter += 1

        return position_id

    def cancel_liquidity(self, entry_id: int) -> None:
        self.entries.pop(entry_id)

    def add_claim_shares(
        self, event_id: int, position_id: int, shares: Decimal
    ) -> None:
        provider = self.positions[position_id].provider
        claim_key = ClaimKey(event_id, position_id)
        default_claim = Claim(shares=Decimal(0), provider=provider)
        claim = self.claims.get(claim_key, default_claim)
        claim.shares += shares
        self.claims[claim_key] = claim

        event = self.events[event_id]
        event.locked_shares += shares
        assert claim.shares <= event.total_shares
        self.events[event_id] = event

        self.active_liquidity_f -= event.get_provided_for_shares_f(shares)

    def iter_impacted_event_ids(self, position_id: int) -> Iterator[int]:
        position = self.positions[position_id]
        for event_id in self.active_events:
            event = self.events[event_id]
            if event.created_counter > position.added_counter:
                yield event_id
        return

    def calc_claim_payout(self, position_id: int, shares: Decimal) -> Decimal:
        total_liquidity_f = self.calc_total_liquidity_f()
        active_fraction_f = Decimal(0)

        for event_id in self.iter_impacted_event_ids(position_id):
            event = self.events[event_id]
            active_fraction_f += event.active_fraction_f

        provider_liquidity_f = quantize(
            total_liquidity_f * shares / self.total_shares
        )

        # TODO: maybe replace this high precision Decimals with Fractions?
        free_fraction_f = self.precision - active_fraction_f
        free_fraction_f = 0 if free_fraction_f < 0 else free_fraction_f
        expected_amount_f = provider_liquidity_f * free_fraction_f / self.precision
        expected_amount = quantize(expected_amount_f / self.precision)
        assert expected_amount >= Decimal(0)
        return expected_amount

    def claim_liquidity(self, position_id: int, shares: Decimal) -> Decimal:
        if shares == 0:
            return Decimal(0)

        payout = self.calc_claim_payout(position_id, shares)
        position = self.positions[position_id]
        position.remove_shares(shares)

        for event_id in self.iter_impacted_event_ids(position_id):
            self.add_claim_shares(event_id, position_id, shares)

        self.total_shares -= shares
        assert self.total_shares >= Decimal(0)

        self.balance -= payout
        assert self.balance >= Decimal(0)

        return payout

    def withdraw_liquidity(
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

        locked_amount_f = event.get_result_for_shares_f(event.locked_shares)
        self.withdrawable_liquidity_f += locked_amount_f

        left_shares = event.total_shares - event.locked_shares
        self.active_liquidity_f -= event.get_provided_for_shares_f(left_shares)
        assert self.active_liquidity_f >= Decimal(0)

        self.active_events.remove(event_id)
        self.balance += amount

    def calc_next_event_liquidity(self) -> Decimal:
        max_liquidity_f = quantize(
            self.calc_total_liquidity_f() / self.max_events
        )
        liquidity_f = min(max_liquidity_f, self.calc_free_liquidity_f())
        return quantize(liquidity_f / self.precision)

    def calc_liquidity_units(self, duration: int, amount: Decimal) -> Decimal:
        liquidity_units = quantize(
            Decimal(duration) * amount / self.total_shares
        )
        assert liquidity_units >= 0
        return liquidity_units

    def create_event(self, line_id: int, next_event_id: int) -> int:
        assert not next_event_id in self.events
        provided_amount = self.calc_next_event_liquidity()
        active_fraction_f = quantize_up(self.precision / self.max_events)

        self.events[next_event_id] = Event(
            created_counter=self.counter,
            active_fraction_f=active_fraction_f,
            total_shares=self.total_shares,
            locked_shares=Decimal(0),
            result=None,
            provided=provided_amount,
            precision=self.precision,
        )

        self.counter += 1
        self.active_liquidity_f += provided_amount * self.precision
        line = self.lines[line_id]
        line.update_last_bets_close_time(self.now)
        duration = line.calc_duration(self.now)
        liquidity_units = self.calc_liquidity_units(duration, provided_amount)
        self.liquidity_units += liquidity_units
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
