from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class DepositLiquidityTestCase(LineAggregatorBaseTestCase):
    def test_should_fail_if_added_zero_liquidity(self):
        self.add_line()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.deposit_liquidity(amount=0)
        msg = 'Should provide tez'
        self.assertTrue(msg in str(cm.exception))

