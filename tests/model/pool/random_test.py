from decimal import Decimal
from unittest import TestCase

from models.pool import PoolModel
from random import choice, randint, seed


class RandomTester:
    users = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'manager']

    def __init__(self, model):
        self.model = model
        self.seed = randint(0, 10**16)
        self.balances = {user: Decimal(0) for user in self.users}
        seed(self.seed)

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
        random_shares = (
            randint(1, position.shares) if position.shares > 1 else 0
        )
        payout = self.model.claim_liquidity(
            position_id=position_id,
            shares=random_shares
        )
        self.balances[position.provider] += payout

    def random_action(self):
        actions = [
            *[self.random_deposit] * 5,
            *[self.random_cancel] * 1,
            *[self.random_approve] * 6,
            *[self.random_claim] * 5,
        ]
        action = choice(actions)
        action()

    def run(self, iterations=1000):
        for iteration in range(iterations):
            self.random_action()
            self.check_invariants()


# TODO: WIP, need to add different methods
class PoolRandomModelTest(TestCase):
    def test_should_preserve_all_invariants(self):
        model = PoolModel()
        tester = RandomTester(model)
        tester.run(iterations=1000)
