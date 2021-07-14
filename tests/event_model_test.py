from unittest import TestCase
from event_model import EventModel


class EventModelTest(TestCase):
    def test_bet_pool_a_win(self):
        event = EventModel(fee=0.03, winning_pool='aboveEq', a=1_000_000, b=1_000_000)
        event.bet('user', 1_000_000, 'aboveEq', 0)
        self.assertTrue(event.diffs['user'] == 500_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 500_000)

    def test_bet_pool_b_win(self):
        event = EventModel(fee=0, winning_pool='below', a=4_000_000, b=1_000_000)
        event.bet('user', 1_000_000, 'below', 1)
        self.assertTrue(event.diffs['user'] == 2_000_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

    def test_bet_pool_b_lose(self):
        event = EventModel(fee=0, winning_pool='aboveEq', a=2_000_000, b=1_000_000)
        event.bet('user', 1_000_000, 'below', 1)
        self.assertTrue(event.diffs['user'] == -1_000_000)
        self.assertTrue(event.pool_a == 1_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

    def test_provide_liquidity(self):
        event = EventModel(fee=0, winning_pool='aboveEq', a=1_000_000, b=1_000_000, total_shares=100)
        event.provide_liquidity('provider', 1_000_000)
        self.assertTrue(event.shares['provider'] == 100)
        self.assertTrue(event.total_shares == 200)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

        event.bet('loser', 2_000_000, 'below', 1)
        self.assertTrue(event.pool_b == 4_000_000)
        self.assertTrue(event.pool_a == 1_000_000)
        self.assertTrue(event.diffs['loser'] == -2_000_000)
        self.assertTrue(event.diffs['provider'] == 1_000_000)

    def test_first_provide_liquidity(self):
        event = EventModel(fee=0, winning_pool='aboveEq', total_shares=100)
        event.provide_liquidity('provider', 4_000_000, 4, 1)
        self.assertTrue(event.pool_a == 4_000_000)
        self.assertTrue(event.pool_b == 1_000_000)
        event.bet('loser', 0, 'below', 1)
        self.assertTrue(event.diffs['loser'] == 0)
        self.assertTrue(event.diffs['provider'] == 0)

    def test_bet_with_fee(self):
        event = EventModel(fee=0.2, winning_pool='aboveEq', a=1_000_000, b=1_000_000)
        event.bet('user', 1_000_000, 'aboveEq', 0.5)
        self.assertTrue(event.diffs['user'] == 450_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 550_000)


    def test_from_storage(self):
        pass

        # TODO: test from_storage
        # TODO: test __eq__ with two same objects
        # TODO: test __eq__ with two different objects

