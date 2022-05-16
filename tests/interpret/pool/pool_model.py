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


rounding_down_context = Context(rounding=ROUND_DOWN)


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

    @classmethod
    def from_storage(cls, storage: AnyStorage) -> Event:
        return cls(
            created_counter=storage['createdCounter'],
            shares=Decimal(storage['shares']),
            total_shares=Decimal(storage['totalShares']),
            locked_shares=Decimal(storage['lockedShares']),
            result=Decimal(storage['result']) if storage['result'] else None,
            provided=Decimal(storage['provided'])
        )

    # TODO: make precision global // add precision to event params?
    def get_result_for_shares(self, shares: Decimal, precision: Decimal) -> Decimal:
        result = self.result if self.result is not None else Decimal(0)
        return (
            result * shares * precision / self.total_shares
        ).quantize(Decimal(1), context=rounding_down_context)

    def get_active_amount(self, precision: Decimal) -> Decimal:
        provided = self.provided * precision
        locked = self.locked_shares * provided / self.total_shares
        return provided - locked


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

        claims = {
            ClaimKey.from_tuple(index): Claim.from_storage(claim)
            for index, claim in storage['claims'].items()
        }

        return cls(
            active_events=list(storage['activeEvents'].keys()),
            positions=convert(Position, storage['positions']),
            total_shares=Decimal(storage['totalShares']),
            events=convert(Event, storage['events']),
            entries=convert(Entry, storage['entries']),
            claims=claims,
            max_events=storage['maxEvents'],
            counter=storage['counter'],
            precision=Decimal(storage['precision']),
            liquidity_units=Decimal(storage['liquidityUnits']),
            balance=balance,
            next_entry_id=storage['nextEntryId'],
            next_position_id=storage['nextPositionId'],
            entry_lock_period=storage['entryLockPeriod'],
            now=now
        )

    def update_max_lines(self, max_lines: int) -> PoolModel:
        ...
        return self

    def quantize(self, value):
        return Decimal(value).quantize(
            Decimal(1),
            context=rounding_down_context
        )

    def calc_active_liquidity(self):
        return self.quantize(sum(
            self.events[event_id].get_active_amount(self.precision)
            for event_id in self.active_events
        ))

    def calc_withdrawable_liquidity(self):
        return self.quantize(sum(
            self.events[claim_key.event_id].get_result_for_shares(
                shares=claim.shares,
                precision=self.precision
            )
            for claim_key, claim in self.claims.items()
        ))

    def calc_entry_liquidity(self):
        return self.quantize(sum(
            entry.amount * self.precision for entry in self.entries.values()
        ))

    def calc_free_liquidity(self):
        return (
            self.balance * self.precision
            - self.calc_withdrawable_liquidity()
            - self.calc_entry_liquidity()
        )

    def calc_total_liquidity(self):
        return self.calc_free_liquidity() + self.calc_active_liquidity()

    def calc_deposit_shares(self, amount: Decimal):
        is_first_deposit = self.total_shares == 0
        if is_first_deposit:
            return amount

        return (amount
            * self.precision
            * self.total_shares
            / self.calc_total_liquidity()
        ).quantize(Decimal(1), context=rounding_down_context)

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

    def claim(self, position_id: int, shares: Decimal) -> PoolModel:
        ...
        return self

    def withdraw(self, position_id: int, event_id: int) -> PoolModel:
        ...
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

