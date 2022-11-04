import unittest

from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class WithdrawLiquidityTestCase(PoolBaseTestCase):
    def test_should_fail_if_trying_to_withdraw_not_finished_event(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_entry()
        self.create_event(next_event_id=0)
        self.claim_liquidity(provider=self.a)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw_claims(
                sender=self.a, claims=[{'eventId': 0, 'provider': self.a}]
            )
        msg = 'Event result is not received yet'
        self.assertTrue(msg in str(cm.exception))

    def test_should_fail_if_trying_to_withdraw_position_with_no_claim(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_entry(entry_id=0)
        self.deposit_liquidity(sender=self.b)
        self.approve_entry(entry_id=1)
        self.create_event(next_event_id=0)
        self.claim_liquidity(provider=self.a)
        self.pay_reward(event_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw_claims(
                sender=self.b, claims=[{'eventId': 0, 'provider': self.b}]
            )
        msg = 'Claim is not found'
        self.assertTrue(msg in str(cm.exception))

    def test_anyone_can_call_withdraw_for_finished_position(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_entry()
        self.create_event(next_event_id=0)
        self.claim_liquidity(provider=self.a)
        self.pay_reward(event_id=0)

        self.withdraw_claims(
            sender=self.b, claims=[{'eventId': 0, 'provider': self.a}]
        )

    def test_multiple_withdraw_should_be_possible(self):
        self.add_line(max_events=5)
        self.deposit_liquidity(sender=self.a)
        self.approve_entry(entry_id=0)
        self.deposit_liquidity(sender=self.b)
        self.approve_entry(entry_id=1)

        for _ in range(5):
            self.create_event()
            self.wait(3600)

        self.claim_liquidity(provider=self.a, sender=self.a)
        self.claim_liquidity(provider=self.b, sender=self.b)

        for event_id in range(5):
            self.pay_reward(event_id=event_id)

        claims = [
            {'eventId': event_id, 'provider': provider}
            for event_id in range(5)
            for provider in [self.a, self.b]
        ]

        amounts = self.withdraw_claims(sender=self.a, claims=claims)
        self.assertEqual(len(amounts), 2)

    @unittest.skip('this is known issue and test represents it:')
    def test_withdrawable_liquidity_should_not_lock_funds_on_contract(self):
        self.add_line(max_events=1)

        self.deposit_liquidity(sender=self.a, amount=1000)
        self.deposit_liquidity(sender=self.b, amount=1000)
        self.deposit_liquidity(sender=self.c, amount=1000)
        self.approve_entry(entry_id=0)
        self.approve_entry(entry_id=1)
        self.approve_entry(entry_id=2)

        self.create_event()
        self.claim_liquidity(provider=self.a, sender=self.a, shares=1000)
        self.claim_liquidity(provider=self.b, sender=self.b, shares=1000)
        self.claim_liquidity(provider=self.c, sender=self.c, shares=1000)
        self.pay_reward(event_id=0, amount=1000)

        claims = [
            {'eventId': 0, 'provider': self.a},
            {'eventId': 0, 'provider': self.b},
            {'eventId': 0, 'provider': self.c},
        ]

        amounts = self.withdraw_claims(sender=self.a, claims=claims)

        # This assert fails because there 1 mutez left in contract:
        self.assertEqual(self.storage['withdrawableLiquidity'], 0)
