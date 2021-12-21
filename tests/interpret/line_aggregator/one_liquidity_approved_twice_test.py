from pytezos import MichelsonRuntimeError
from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class OneLiquidityApprovedTwiceTestCase(LineAggregatorBaseTestCase):
    def test_should_fail_when_try_to_approve_liquidity_twice(self):

        # creating default event:
        self.add_line(max_active_events=10)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=80_000_000)
        self.approve_liquidity(self.a, entry_position_id=0)
        self.assertEqual(self.storage['nextEventLiquidity'], 8_000_000)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(self.a, entry_position_id=0)
        msg = 'Entry position is not found'
        self.assertTrue(msg in str(cm.exception))

