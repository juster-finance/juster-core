from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class DepositLiquidityTestCase(PoolBaseTestCase):
    def test_should_fail_if_added_zero_liquidity(self):
        self.add_line()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.deposit_liquidity(amount=0)
        msg = 'Should provide tez'
        self.assertTrue(msg in str(cm.exception))


    def test_should_be_able_to_deposit_liquidity(self):
        self.add_line()
        self.deposit_liquidity(amount=1000)

