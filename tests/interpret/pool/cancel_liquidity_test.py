from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class CancelLiquidityTestCase(PoolBaseTestCase):
    def test_should_allow_to_cancel_liquidity_after_it_was_added(self):
        self.add_line()
        self.deposit_liquidity()
        self.cancel_liquidity()


    def test_should_not_be_able_to_cancel_others_liquidity(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity(sender=self.b)
        msg = 'Not entry position owner'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_be_able_to_cancel_liquidity_after_it_was_approved(self):
        self.add_line()
        self.deposit_liquidity()
        self.approve_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity()
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_be_able_to_approve_liquidity_after_it_was_canceled(self):
        self.add_line()
        self.deposit_liquidity()
        self.cancel_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity()
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))

