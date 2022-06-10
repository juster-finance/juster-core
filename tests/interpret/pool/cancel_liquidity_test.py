from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class CancelLiquidityTestCase(PoolBaseTestCase):
    def test_should_allow_to_cancel_liquidity_if_deposit_is_paused(self):
        self.add_line()
        self.deposit_liquidity()
        self.trigger_pause_deposit()
        self.cancel_liquidity()

    def test_should_not_allow_to_cancel_if_deposit_is_not_paused(self):
        self.add_line()
        self.deposit_liquidity()
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity()
        msg = 'Cancel is not allowed'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_be_able_to_cancel_others_liquidity(self):
        # TODO: should it?
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.trigger_pause_deposit()
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity(sender=self.b)
        msg = 'Not entry position owner'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_be_able_to_cancel_liquidity_after_it_was_approved(
        self,
    ):
        self.add_line()
        self.deposit_liquidity()
        self.approve_liquidity()
        self.trigger_pause_deposit()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity()
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_be_able_to_approve_liquidity_after_it_was_canceled(
        self,
    ):
        self.add_line()
        self.deposit_liquidity()
        self.trigger_pause_deposit()
        self.cancel_liquidity()
        self.trigger_pause_deposit()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity()
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_be_able_to_cancel_liquidity_twice(self):
        self.add_line()
        entry_id = self.deposit_liquidity()
        self.trigger_pause_deposit()
        self.cancel_liquidity(entry_id=entry_id)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.cancel_liquidity(entry_id=entry_id)
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))
