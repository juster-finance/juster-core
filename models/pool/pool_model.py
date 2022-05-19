from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from typing import Any
from typing import Optional
from typing import Type

from models.pool.claim import Claim
from models.pool.claim_key import ClaimKey
from models.pool.entry import Entry
from models.pool.event import Event
from models.pool.helpers import quantize
from models.pool.line import Line
from models.pool.position import Position
from models.pool.types import AnyStorage


@dataclass
class PoolModel:
    """ Model that emulates simplified Pool case with one event line """

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
    active_liquidity: Decimal = Decimal(0)
    withdrawable_liquidity: Decimal = Decimal(0)
    lines: dict[int, Line] = field(default_factory=dict)
    next_line_id: int = 0

    @classmethod
    def from_storage(
        cls: Type[PoolModel],
        storage: AnyStorage,
        balance: Decimal=Decimal(0),
        now: int=0
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
            active_liquidity=Decimal(storage['activeLiquidityF']),
            withdrawable_liquidity=Decimal(storage['withdrawableLiquidityF']),
            lines=convert(Line, storage['lines']),
            next_line_id=storage['nextLineId']
        )

    def trigger_pause_line(self, line_id: int) -> PoolModel:
        line = self.lines[line_id]
        diff = line.max_events
        self.max_events += diff if line.is_paused else -diff
        line.is_paused = not line.is_paused
        return self

    def add_line(
        self,
        measure_period: int,
        bets_period: int,
        last_bets_close_time: int,
        max_events: int,
        is_paused: bool,
        min_betting_period: int
    ) -> PoolModel:
        self.lines[self.next_line_id] = Line(
            measure_period=measure_period,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time,
            max_events=max_events,
            is_paused=is_paused,
            min_betting_period=min_betting_period
        )
        self.next_line_id += 1
        self.max_events += 0 if is_paused else max_events
        return self

    def calc_entry_liquidity(self):
        return quantize(sum(
            entry.amount * self.precision for entry in self.entries.values()
        ))

    def calc_free_liquidity(self):
        return (
            self.balance * self.precision
            - self.withdrawable_liquidity
            - self.calc_entry_liquidity()
        )

    def calc_total_liquidity(self):
        return self.calc_free_liquidity() + self.active_liquidity

    def calc_deposit_shares(self, amount: Decimal):
        is_first_deposit = self.total_shares == 0
        if is_first_deposit:
            return amount

        return quantize(
            amount
            * self.precision
            * self.total_shares
            / self.calc_total_liquidity()
        )

    def calc_withdraw_payouts_f(
        self,
        claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts: dict[str, Decimal] = {}
        for claim_key in claim_keys:
            claim = self.claims[claim_key]
            event = self.events[claim_key.event_id]
            payout = payouts.get(claim.provider, Decimal(0))
            payout += event.get_result_for_shares(claim.shares)
            payouts[claim.provider] = payout

        return payouts

    def calc_withdraw_payouts(
        self,
        claim_keys: list[ClaimKey]
    ) -> dict[str, Decimal]:
        payouts_f = self.calc_withdraw_payouts_f(claim_keys)
        return {
            address: quantize(payout_f/self.precision)
            for address, payout_f in payouts_f.items()
        }

    def deposit_liquidity(self, user: str, amount: Decimal) -> PoolModel:
        accept_after = self.now + self.entry_lock_period
        entry = Entry(user, amount, accept_after)
        self.entries[self.next_entry_id] = entry
        self.next_entry_id += 1
        self.balance += amount

        return self

    def approve_liquidity(self, entry_id: int) -> PoolModel:
        entry = self.entries[entry_id]
        position = Position(
            provider=entry.provider,
            shares=self.calc_deposit_shares(entry.amount),
            added_counter=self.counter
        )
        self.entries.pop(entry_id)

        self.positions[self.next_position_id] = position
        self.next_position_id += 1
        self.total_shares += position.shares
        self.counter += 1

        return self

    def cancel_liquidity(self, entry_id: int) -> PoolModel:
        self.entries.pop(entry_id)
        return self

    def add_claim_shares(
        self,
        event_id: int,
        position_id: int,
        shares: Decimal
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

        self.active_liquidity -= event.get_provided_for_shares(shares)

    def iter_impacted_event_ids(self, position_id: int):
        position = self.positions[position_id]
        for event_id in self.active_events:
            event = self.events[event_id]
            if event.created_counter > position.added_counter:
                yield event_id
        return

    def calc_claim_payout(
        self,
        position_id: int,
        shares: Decimal
    ) -> Decimal:
        total_liquidity = self.calc_total_liquidity()
        locked_liquidity = Decimal(0)
        for event_id in self.iter_impacted_event_ids(position_id):
            event = self.events[event_id]
            locked_liquidity += quantize(
                total_liquidity
                * shares
                * event.shares
                / event.total_shares
                / self.total_shares
            )

        provider_liquidity = quantize(
            total_liquidity
            * shares
            / self.total_shares
        )

        # TODO: should all high precision variables marked with f?
        # TODO: maybe replace this high precision Decimals with Fractions?
        expected_amount_f = provider_liquidity - locked_liquidity
        expected_amount = quantize(expected_amount_f / self.precision)
        return expected_amount

    def claim_liquidity(self, position_id: int, shares: Decimal) -> PoolModel:
        if shares == 0:
            return self
        payout = self.calc_claim_payout(position_id, shares)
        position = self.positions[position_id]
        position.remove_shares(shares)

        for event_id in self.iter_impacted_event_ids(position_id):
            self.add_claim_shares(event_id, position_id, shares)

        self.total_shares -= shares
        self.balance -= payout
        assert self.balance >= Decimal(0)

        return self

    def withdraw_liquidity(self, claim_keys: list[ClaimKey]) -> PoolModel:
        payouts_f = self.calc_withdraw_payouts_f(claim_keys)
        payouts = self.calc_withdraw_payouts(claim_keys)
        [self.claims.pop(key) for key in claim_keys]
        self.withdrawable_liquidity -= sum(payouts_f.values())
        self.balance -= sum(payouts.values())
        return self

    def pay_reward(self, event_id: int, amount: Decimal) -> PoolModel:
        event = self.events[event_id]
        event.result = amount

        locked_amount = event.get_result_for_shares(event.locked_shares)
        self.withdrawable_liquidity += locked_amount

        left_shares = event.total_shares - event.locked_shares
        self.active_liquidity -= event.get_provided_for_shares(left_shares)
        assert self.active_liquidity >= Decimal(0)

        self.active_events.remove(event_id)
        self.balance += amount
        return self

    def calc_next_event_liquidity(self) -> Decimal:
        max_liquidity = quantize(
            self.calc_total_liquidity()
            / self.max_events
        )
        liquidity_f = min(max_liquidity, self.calc_free_liquidity())
        return quantize(liquidity_f / self.precision)

    def calc_liquidity_units(self, duration: int, amount: Decimal) -> Decimal:
        liquidity_units = quantize(
            Decimal(duration)
            * amount
            / self.total_shares
        )
        assert liquidity_units >= 0
        return liquidity_units

    def create_event(self, line_id: int, next_event_id: int) -> PoolModel:
        assert not next_event_id in self.events
        shares = quantize(self.total_shares / self.max_events)
        provided_amount = self.calc_next_event_liquidity()

        self.events[next_event_id] = Event(
            created_counter=self.counter,
            shares=shares,
            total_shares=self.total_shares,
            locked_shares=Decimal(0),
            result=None,
            provided=provided_amount,
            precision=self.precision
        )

        self.counter += 1
        self.active_liquidity += provided_amount * self.precision
        line = self.lines[line_id]
        line.update_last_bets_close_time(self.now)
        duration = line.calc_duration(self.now)
        liquidity_units = self.calc_liquidity_units(duration, provided_amount)
        self.liquidity_units += liquidity_units
        self.balance -= provided_amount
        self.active_events.append(next_event_id)
        assert self.balance >= Decimal(0)

        return self

    def default(self, amount: Decimal) -> PoolModel:
        self.balance += amount
        return self

    def diff_with(self, other: PoolModel) -> list[str]:
        """ Returns attributes that different with other """
        return [
            attr_name for attr_name, attr_value in self.__dict__.items()
            if attr_value != getattr(other, attr_name)
        ]

