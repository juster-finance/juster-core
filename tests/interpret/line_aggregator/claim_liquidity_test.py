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
        self.approve_liquidity(entry_position_id=0)
        self.approve_liquidity(entry_position_id=1)
        self.create_event(event_line_id=0)
        self.create_event(event_line_id=1)

        self.claim_liquidity(sender=self.a, position_id=0, shares=100)
        target_claims = {
            (0, 0): {'shares': 100, 'totalShares': 400},
            (1, 0): {'shares': 100, 'totalShares': 400}
        }
        self.assertDictEqual(self.storage['claims'], target_claims)

        self.claim_liquidity(sender=self.b, position_id=1, shares=100)
        target_claims = {
            (0, 0): {'shares': 100, 'totalShares': 400},
            (1, 0): {'shares': 100, 'totalShares': 400},
            (0, 1): {'shares': 100, 'totalShares': 400},
            (1, 1): {'shares': 100, 'totalShares': 400}
        }
        self.assertDictEqual(self.storage['claims'], target_claims)


    def test_should_return_unused_liquidity_amount(self):
        pass
