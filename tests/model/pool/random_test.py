from decimal import Decimal
from unittest import TestCase

from models.pool import PoolModel
from random import choice, randint, seed


def rand_from_zero_to(value_to):
    return randint(0, value_to) if value_to > 0 else value_to


class RandomTester:
    users = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'manager']
    max_events = 18

    def __init__(self, model):
        self.model = model
        self.seed = randint(0, 10**16)
        self.balances = {user: Decimal(0) for user in self.users}
        self.balances['juster_core'] = Decimal(0)
        seed(self.seed)
        self.next_event_id = 0

    def check_invariants(self):
        assert sum(self.balances.values()) + self.model.balance == 0
        # TODO: active liquidity equals to the amount in juster core
        # TODO: sum of claims for finished events equals to withdrawable liquidity
        # TODO: ?

    def random_user(self):
        return choice(self.users)

    def random_deposit(self):
        user = self.random_user()
        amount = choice([0, 1, 1000, 1_000_000, 1000_000_000])
        self.balances[user] -= amount
        self.model.deposit_liquidity(user=user, amount=amount)

    def random_cancel(self):
        if not len(self.model.entries):
            return
        entry_id = choice(list(self.model.entries.keys()))
        entry = self.model.entries[entry_id]
        self.balances[entry.provider] += entry.amount
        self.model.cancel_liquidity(entry_id=entry_id)

    def random_approve(self):
        if not len(self.model.entries):
            return
        entry_id = choice(list(self.model.entries.keys()))
        entry = self.model.entries[entry_id]
        self.model.approve_liquidity(entry_id=entry_id)

    def random_claim(self):
        if not len(self.model.positions):
            return
        position_id = choice(list(self.model.positions.keys()))
        position = self.model.positions[position_id]
        random_shares = rand_from_zero_to(position.shares)

        payout = self.model.claim_liquidity(
            position_id=position_id,
            shares=random_shares
        )
        self.balances[position.provider] += payout

    def random_create_event(self):
        if len(self.model.active_events) > self.max_events:
            return
        if self.model.calc_free_liquidity_f() == 0:
            return

        self.balances['juster_core'] += self.model.calc_next_event_liquidity()
        self.model.create_event(line_id=0, next_event_id=self.next_event_id)
        self.next_event_id += 1

    def random_withdraw(self):
        claim_keys = list(self.model.claims.keys())
        claims_count = rand_from_zero_to(len(claim_keys))

        while len(claim_keys) > claims_count:
            claim_keys.pop(rand_from_zero_to(len(claim_keys) - 1))

        payouts = self.model.withdraw_liquidity(claim_keys)
        for user, payout in payouts.items():
            self.balances[user] += payout

    def random_action(self):
        actions = [
            *[self.random_deposit] * 5,
            *[self.random_cancel] * 1,
            *[self.random_approve] * 6,
            *[self.random_claim] * 5,
            *[self.random_withdraw] * 5,
            *[self.random_create_event] * 20,
            # *[self.random_pay_reward] * 20,
            # *[self.random_default] * 10,
            # TODO: random trigger pause line/deposits?
        ]
        action = choice(actions)
        action()

    def run(self, iterations=1000):
        self.model.add_line(
            measure_period=3600,
            bets_period=3600,
            last_bets_close_time=0,
            max_events=self.max_events,
            is_paused=False,
            min_betting_period=0,
        )

        for iteration in range(iterations):
            self.random_action()
            self.check_invariants()


# TODO: WIP, need to add different methods
class PoolRandomModelTest(TestCase):
    def test_should_preserve_all_invariants(self):
        model = PoolModel()
        tester = RandomTester(model)
        tester.run(iterations=1000)
