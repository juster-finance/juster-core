import unittest
from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError
from random import randint


class ClaimLiquidityTestCase(LineAggregatorBaseTestCase):
    def test_should_not_allow_claim_more_shares_that_in_position(self):

        self.add_line()
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_liquidity(position_id=0, shares=101)
        msg = 'Claim shares is exceed position shares'
        self.assertTrue(msg in str(cm.exception))


    def test_should_create_positions_for_all_events_after_claim(self):
        self.add_line()
        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=100)
        self.deposit_liquidity(sender=self.b, amount=300)
        self.approve_liquidity(entry_id=0)
        self.approve_liquidity(entry_id=1)
        self.create_event(event_line_id=0)
        self.create_event(event_line_id=1)

        self.claim_liquidity(sender=self.a, position_id=0, shares=100)
        target_claims = {
            (0, 0): {'shares': 100, 'totalShares': 400, 'provider': self.a},
            (1, 0): {'shares': 100, 'totalShares': 400, 'provider': self.a}
        }
        self.assertDictEqual(self.storage['claims'], target_claims)

        self.claim_liquidity(sender=self.b, position_id=1, shares=100)
        target_claims = {
            (0, 0): {'shares': 100, 'totalShares': 400, 'provider': self.a},
            (1, 0): {'shares': 100, 'totalShares': 400, 'provider': self.a},
            (0, 1): {'shares': 100, 'totalShares': 400, 'provider': self.b},
            (1, 1): {'shares': 100, 'totalShares': 400, 'provider': self.b}
        }
        self.assertDictEqual(self.storage['claims'], target_claims)


    def test_should_return_unused_liquidity_amount(self):
        self.add_line(max_active_events=2)
        self.deposit_liquidity(sender=self.a, amount=100)
        self.approve_liquidity(entry_id=0)
        self.assertEqual(self.balances[self.a], -100)

        # 50 mutez used in the first event (100 / 2 max active events):
        self.create_event(event_line_id=0)
        self.claim_liquidity(sender=self.a, position_id=0, shares=100)

        # 50 mutez unused liquidity should be returned:
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
        msg = 'Position is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_be_possible_to_claim_more_shares_than_have(self):
        self.add_line()
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_liquidity(position_id=0, shares=101)
        msg = 'Claim shares is exceed position shares'
        self.assertTrue(msg in str(cm.exception))


    def test_should_be_possible_to_claim_partial_liquidity(self):
        self.add_line()
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity()
        self.create_event(event_line_id=0)

        self.claim_liquidity(position_id=0, shares=50)
        self.claim_liquidity(position_id=0, shares=30)
        self.claim_liquidity(position_id=0, shares=15)
        self.claim_liquidity(position_id=0, shares=3)
        self.claim_liquidity(position_id=0, shares=2)

        target_claims = {
            (0, 0): {
                'shares': 100,
                'provider': self.a,
                'totalShares': 100},
        }

        self.assertDictEqual(self.storage['claims'], target_claims)


    def test_should_not_create_claims_for_zero_shares(self):
        self.add_line()
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity()
        self.create_event(event_line_id=0)

        self.claim_liquidity(position_id=0, shares=0)
        self.assertEqual(len(self.storage['claims']), 0)


    def test_should_not_increase_claimed_shares_for_not_affected_events(self):
        self.add_line(max_active_events=2)
        self.deposit_liquidity(amount=100, sender=self.a)
        self.approve_liquidity(entry_id=0)
        self.create_event(event_line_id=0)

        self.deposit_liquidity(amount=100, sender=self.b)
        self.approve_liquidity(entry_id=1)

        self.claim_liquidity(position_id=1, shares=100, sender=self.b)
        self.assertEqual(self.storage['events'][0]['lockedShares'], 0)

