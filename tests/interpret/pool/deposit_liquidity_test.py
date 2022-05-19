from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


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


    def test_should_allow_to_withdraw_all_liquidity_and_add_new(self):
        self.add_line()
        self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id=0)
        self.assertEqual(self.storage['totalShares'], 1000)
        self.claim_liquidity(position_id=0, shares=1000)
        self.assertEqual(self.storage['totalShares'], 0)

        self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id=1)
        self.assertEqual(self.storage['totalShares'], 1000)

