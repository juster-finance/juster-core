from __future__ import annotations
import json
from decimal import Decimal
from typing import Optional
from typing import Any
from typing import Type
from typing import TypeVar
from dataclasses import dataclass
from dataclasses import field
from decimal import Context, ROUND_DOWN


def quantize(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        Decimal(1),
        context=Context(rounding=ROUND_DOWN)
    )


AnyStorage = dict[str, Any]

# TODO: add models directory at the root and here might be pool dir with all
# classes splitted in separate files

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


@dataclass
class Position:
    provider: str
    shares: Decimal
    added_counter: int

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Position:
        return cls(
            provider=storage['provider'],
            shares=Decimal(storage['shares']),
            added_counter=storage['addedCounter']
        )

    def remove_shares(self, shares: Decimal):
        self.shares -= shares
        assert self.shares >= 0

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

@dataclass
class Event:
    created_counter: int
    shares: Decimal
    total_shares: Decimal
    locked_shares: Decimal
    result: Optional[Decimal]
    provided: Decimal
    precision: Decimal

    @classmethod
    def from_storage(cls, storage: AnyStorage, precision: Decimal) -> Event:
        return cls(
            created_counter=storage['createdCounter'],
            shares=Decimal(storage['shares']),
            total_shares=Decimal(storage['totalShares']),
            locked_shares=Decimal(storage['lockedShares']),
            result=Decimal(storage['result']) if storage['result'] else None,
            provided=Decimal(storage['provided']),
            precision=precision
        )

    def get_result_for_shares(self, shares: Decimal) -> Decimal:
        result = self.result if self.result is not None else Decimal(0)
        return quantize(
            result
            * shares
            * self.precision
            / self.total_shares
        )

    def get_provided_for_shares(self, shares: Decimal) -> Decimal:
        return quantize(
            self.provided
            * shares
            * self.precision
            / self.total_shares
        )


@dataclass
class PoolModel:
    """ Model that emulates simplified Pool case with one event line """

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
            active_liquidity=storage['activeLiquidityF']
        )

    def update_max_lines(self, max_lines: int) -> PoolModel:
        ...
        return self

    def calc_withdrawable_liquidity(self):
        return quantize(sum(
            self.events[claim_key.event_id].get_result_for_shares(claim.shares)
            for claim_key, claim in self.claims.items()
        ))

    def calc_entry_liquidity(self):
        return quantize(sum(
            entry.amount * self.precision for entry in self.entries.values()
        ))

    def calc_free_liquidity(self):
        return (
            self.balance * self.precision
            - self.calc_withdrawable_liquidity()
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

    def calc_withdraw_payouts(
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

    def deposit(self, user: str, amount: Decimal) -> PoolModel:
        accept_after = self.now + self.entry_lock_period
        entry = Entry(user, amount, accept_after)
        self.entries[self.next_entry_id] = entry
        self.next_entry_id += 1
        self.balance += amount

        return self

    def approve(self, entry_id: int) -> PoolModel:
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

    def cancel(self, entry_id: int) -> PoolModel:
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
        expected_amount_f = provider_liquidity - locked_liquidity
        expected_amount = quantize(expected_amount_f / self.precision)
        return expected_amount

    def claim(self, position_id: int, shares: Decimal) -> PoolModel:
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

    def withdraw(self, claim_keys: list[ClaimKey]) -> PoolModel:
        payouts = self.calc_withdraw_payouts(claim_keys)
        self.balance -= sum(payouts.values())
        [self.claims.pop(key) for key in claim_keys]
        return self

    def pay_reward(self, event_id: int, amount: Decimal) -> PoolModel:
        ...
        return self

    def create_event(self, line_id: int) -> PoolModel:
        ...
        return self

    def default(self, amount: Decimal) -> PoolModel:
        ...
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PoolModel):
            return NotImplemented

        # TODO: it is possible to sort active_events in other places and
        # then this method is probably not necessary
        comparsions = {
            'active_events': sorted(self.active_events) == sorted(other.active_events),
            'positions': self.positions == other.positions,
            'events': self.events == other.events,
            'entries': self.entries == other.entries,
            'claims': self.claims == other.claims,
            'total_shares': self.total_shares == other.total_shares,
            'max_events': self.max_events == other.max_events,
            'counter': self.counter == other.counter,
            'precision': self.precision == other.precision,
            'liquidity_units': self.liquidity_units == other.liquidity_units,
            'balance': self.balance == other.balance,
            'next_position_id': self.next_position_id == other.next_position_id,
            'next_entry_id': self.next_entry_id == other.next_entry_id,
            'entry_lock_period': self.entry_lock_period == other.entry_lock_period,
            'now': self.now == other.now,
            'active_liquidity': self.active_liquidity == other.active_liquidity
        }

        is_equal = all(comparsions.values())
        if not is_equal:
            for name, is_same in comparsions.items():
                if not is_same:
                    print(f'{name} is not equal:')
                    print(getattr(self, name))
                    print(getattr(other, name))
            import pdb; pdb.set_trace()

        return is_equal

