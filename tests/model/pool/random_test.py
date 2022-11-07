from decimal import Decimal
from unittest import TestCase

from models.pool import PoolModel
from random import choice, randint, seed


def rand_from_zero_to(value_to):
    return randint(0, value_to) if value_to > 0 else value_to


class RandomTester:
    # TODO: typing
    users = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'manager']
    max_events = 18

    def __init__(self, model):
        self.model = model
        self.seed = randint(0, 10**16)
        self.balances = {user: Decimal(0) for user in self.users}
        self.balances['juster_core'] = Decimal(0)
        self.balances['bakers'] = Decimal(0)
        # TODO: move balance managemet to pool model?
        seed(self.seed)
        self.next_event_id = 0

    def check_invariants(self):
        assert sum(self.balances.values()) + self.model.balance == 0
        calculated_dps = sum(
            points.amount for points in self.model.duration_points.values()
        )
        assert calculated_dps == self.model.total_duration_points

        active_liquidity_sum = sum(
            event.provided - event.claimed
            for event in self.model.events.values()
            if event.result is None
        )
        active_liquidity_sum_f = active_liquidity_sum * self.model.precision
        assert self.model.active_liquidity_f == active_liquidity_sum_f

        # TODO: there might be more invariants to check
        # TODO: sum of claims for finished events equals to withdrawable liquidity (?)

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
        self.model.cancel_entry(entry_id=entry_id)

    def random_approve(self):
        if not len(self.model.entries):
            return
        entry_id = choice(list(self.model.entries.keys()))
        entry = self.model.entries[entry_id]
        self.model.approve_entry(entry_id=entry_id)

    def random_claim(self):
        if not len(self.model.shares):
            return
        provider = choice(list(self.model.shares.keys()))
        provider_shares = self.model.shares[provider]
        random_shares = rand_from_zero_to(provider_shares)

        payout = self.model.claim_liquidity(
            provider=provider,
            shares=random_shares
        )
        self.balances[provider] += payout

    def random_create_event(self):
        if len(self.model.active_events) > self.max_events:
            return

        next_event_liquidity = self.model.calc_next_event_liquidity()
        if next_event_liquidity == 0:
            return

        if self.model.total_shares == 0:
            return

        self.balances['juster_core'] += next_event_liquidity
        self.model.create_event(line_id=0, next_event_id=self.next_event_id)
        self.next_event_id += 1

    def random_withdraw(self):
        claim_keys = list(self.model.claims.keys())
        claims_count = rand_from_zero_to(len(claim_keys))

        while len(claim_keys) > claims_count:
            claim_keys.pop(rand_from_zero_to(len(claim_keys) - 1))

        payouts = self.model.withdraw_claims(claim_keys)
        for user, payout in payouts.items():
            self.balances[user] += payout

    def random_pay_reward(self):
        if not self.model.active_events:
            return
        event_id = choice(self.model.active_events)
        random_reward = choice([0, 1, 1000, 1_000_000])
        self.model.pay_reward(event_id=event_id, amount=random_reward)
        self.balances['juster_core'] -= random_reward

    def random_default(self):
        random_amount = choice([0, 1, 1000, 1_000_000])
        self.model.default(amount=random_amount)
        self.balances['bakers'] -= random_amount

    def random_action(self):
        actions = [
            *[self.random_deposit] * 5,
            *[self.random_cancel] * 1,
            *[self.random_approve] * 6,
            *[self.random_claim] * 5,
            *[self.random_withdraw] * 5,
            *[self.random_create_event] * 20,
            *[self.random_pay_reward] * 20,
            *[self.random_default] * 10,
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
            self.model.increase_level()
            self.check_invariants()

class PoolRandomModelTest(TestCase):
    def test_should_preserve_all_invariants(self):
        model = PoolModel()
        tester = RandomTester(model)
        tester.run(iterations=1000)
