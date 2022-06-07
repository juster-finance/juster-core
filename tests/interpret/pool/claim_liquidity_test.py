import unittest
from random import randint

from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class ClaimLiquidityTestCase(PoolBaseTestCase):
    def test_should_not_allow_claim_more_shares_that_in_position(self):

        self.add_line()
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_liquidity(position_id=0, shares=101)
        msg = 'Claim shares is exceed position shares'
        self.assertTrue(msg in str(cm.exception))

    def test_should_create_positions_for_all_events_after_claim(self):
        self.add_line(max_events=1)
        self.add_line(max_events=1)
        self.deposit_liquidity(sender=self.a, amount=100)
        self.deposit_liquidity(sender=self.b, amount=300)
        self.approve_liquidity(entry_id=0)
        self.approve_liquidity(entry_id=1)

        # 400 mutez distributed equallty between two events:
        self.create_event(line_id=0)
        self.create_event(line_id=1)

        self.claim_liquidity(sender=self.a, position_id=0, shares=100)
        # claim amount is 200 provided * 100 shares / 400 total shares:
        target_claims = {
            (0, 0): {'amount': 50, 'provider': self.a},
            (1, 0): {'amount': 50, 'provider': self.a},
        }
        self.assertDictEqual(self.storage['claims'], target_claims)

        # claim amount is 150 left provided * 100 shares / 300 total shares:
        self.claim_liquidity(sender=self.b, position_id=1, shares=100)
        target_claims = {
            (0, 0): {'amount': 50, 'provider': self.a},
            (1, 0): {'amount': 50, 'provider': self.a},
            (0, 1): {'amount': 50, 'provider': self.b},
            (1, 1): {'amount': 50, 'provider': self.b},
        }
        self.assertDictEqual(self.storage['claims'], target_claims)

    def test_should_return_free_liquidity_share(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(sender=self.a, amount=100)
        self.approve_liquidity(entry_id=0)
        self.assertEqual(self.balances[self.a], -100)

        # 50 mutez used in the first event (100 / 2 max active events):
        self.create_event(line_id=0)
        payout = self.claim_liquidity(sender=self.a, position_id=0, shares=100)

        # 50 mutez unused liquidity should be returned:
        self.assertEqual(payout, 50)
        self.assertEqual(self.balances[self.a], -50)

    def test_should_not_allow_to_claim_others_shares(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_liquidity()
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_liquidity(sender=self.b)

        msg = 'Not position owner'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_allow_to_claim_shares_twice(self):
        self.add_line()
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()
        self.claim_liquidity(position_id=0, shares=100)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_liquidity(position_id=0, shares=100)
        msg = 'Claim shares is exceed position shares'
        self.assertTrue(msg in str(cm.exception))

    def test_should_be_possible_to_claim_partial_liquidity(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity()
        self.create_event(line_id=0)

        self.claim_liquidity(position_id=0, shares=50)
        self.claim_liquidity(position_id=0, shares=30)
        self.claim_liquidity(position_id=0, shares=15)
        self.claim_liquidity(position_id=0, shares=3)
        self.claim_liquidity(position_id=0, shares=2)

        # as far as there is 2 events, target amount is 100 / 2 = 50
        target_claims = {
            (0, 0): {'amount': 50, 'provider': self.a},
        }

        self.assertDictEqual(self.storage['claims'], target_claims)

    def test_should_not_create_claims_for_zero_shares(self):
        self.add_line()
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity()
        self.create_event(line_id=0)

        self.claim_liquidity(position_id=0, shares=0)
        self.assertEqual(len(self.storage['claims']), 0)

    def test_should_increase_claimed_shares_for_events_created_before_position(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity(entry_id=0)
        self.create_event(line_id=0)

        self.deposit_liquidity(amount=100, sender=self.b)
        self.approve_liquidity(entry_id=1)

        self.claim_liquidity(position_id=1, shares=100, sender=self.b)
        # claimed amount is 100 shares / 200 total shares * 50 provided to event:
        self.assertEqual(self.storage['events'][0]['claimed'], 25)
