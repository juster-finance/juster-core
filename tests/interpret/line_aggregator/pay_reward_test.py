import unittest
from random import randint
from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class PayRewardTestCase(LineAggregatorBaseTestCase):

    @unittest.skip("Need to decide what logic should be implemented in contract")
    def test_pay_reward_for_event_that_was_not_created_by_aggregator(self):
        # TODO: need to decide what is the best practice to do in this case
        # option 1: block this action, because this is definitely wrong state
        # but then it will freeze withdrawals
        # option 2: allow this action, because it can't harm (or can it?)
        # maybe allow this action and act as if it was added to `default`?
        pass

    @unittest.skip("Need to decide what logic should be implemented in contract")
    def test_event_finished_twice(self):
        # TODO: the same as prev: need to decide what is the best practice
        # option 1: block this action, because this is definitely wrong state
        # but then it will freeze withdrawals
        # option 2: allow this action, because it can't harm (or can it?)
        # maybe allow this action and act as if it was added to `default`?
        pass

    def test_pay_reward_finishes_event(self):
        # simple test that checks that after event is finished result is writed:
        self.add_line()
        self.deposit_liquidity()
        self.approve_liquidity()

        # result before finish should be None:
        self.create_event()
        self.assertEqual(self.storage['events'][0]['result'], None)
        self.wait(3600)

        # result after finish should equal to provided amount:
        self.pay_reward(event_id=0, amount=1_000_000)
        self.assertEqual(self.storage['events'][0]['result'], 1_000_000)


    def test_pay_reward_changes_next_event_liquidity_amount(self):
        # creating simple line with one event that should receive random amount of tez
        self.add_line(max_active_events=1)
        random_amount = randint(10, 20) * 100_000
        self.deposit_liquidity(amount=random_amount)
        self.approve_liquidity()

        # as far as there are only one event it should receive all of the liquidity
        self.assertEqual(self.storage['nextEventLiquidity'], random_amount)
        self.create_event()
        self.wait(3600)

        # checking that after event finish with random_amount all this amount
        # should be consideread as nextEventLiquidity:
        random_amount = randint(10, 20) * 100_000
        self.pay_reward(event_id=0, amount=random_amount)
        self.assertEqual(self.storage['nextEventLiquidity'], random_amount)

