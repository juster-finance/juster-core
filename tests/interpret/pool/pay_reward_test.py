import unittest
from random import randint

from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class PayRewardTestCase(PoolBaseTestCase):
    def test_should_fail_to_pay_reward_for_event_that_was_not_created_by_pool(
        self,
    ):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.pay_reward(event_id=100)
        self.assertTrue('Active event is not found' in str(cm.exception))

    def test_should_fail_if_event_finished_twice(self):
        self.add_line()
        self.deposit_liquidity()
        self.approve_liquidity()
        self.create_event(next_event_id=0)
        self.pay_reward(event_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.pay_reward(event_id=0)
        self.assertTrue('Active event is not found' in str(cm.exception))

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
        self.add_line(max_events=1)
        random_amount = randint(10, 20) * 100_000
        self.deposit_liquidity(amount=random_amount)
        self.approve_liquidity()

        # as far as there are only one event it should receive all of the liquidity
        self.assertEqual(self.get_next_liquidity(), random_amount)
        self.create_event()
        self.wait(3600)

        # checking that after event finish with random_amount all this amount
        # should be consideread as nextEventLiquidity:
        random_amount = randint(10, 20) * 100_000
        self.pay_reward(event_id=0, amount=random_amount)
        self.assertEqual(self.get_next_liquidity(), random_amount)

    def test_should_fail_if_wrong_address_tries_to_payout(self):
        # creating simple line with one event that should receive random amount of tez
        self.add_line(max_events=1)
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()
        self.create_event()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.pay_reward(event_id=0, amount=100, sender=self.c)
        msg = 'Address is not expected'
        self.assertTrue(msg in str(cm.exception))

    def test_should_allow_to_run_two_justers_in_different_lines(self):
        self.add_line(max_events=1, juster_address=self.c)
        self.add_line(max_events=1, juster_address=self.d)
        self.deposit_liquidity(amount=100)
        provider = self.approve_liquidity()
        self.create_event(line_id=0)
        self.create_event(line_id=1)

        self.pay_reward(event_id=0, amount=50, sender=self.c)
        self.pay_reward(event_id=1, amount=50, sender=self.d)

        self.claim_liquidity(provider=provider, shares=100)
        self.assertTrue(
            all(balance == 0 for balance in self.balances.values())
        )
