from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class DisbandPoolTestCase(PoolBaseTestCase):
    def test_should_set_disband_allow_if_manager_calls(self):
        self.disband(sender=self.manager)

    def test_should_fail_to_disband_if_not_manager_calls(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.disband(sender=self.c)

        msg = 'Not a contract manager'
        self.assertTrue(msg in str(cm.exception))

    def test_should_allow_to_claim_others_liquidity_if_pool_in_disbanded_state(self):
        self.add_line()
        entry_id = self.deposit_liquidity(sender=self.a)
        position_id = self.approve_liquidity(entry_id=entry_id)
        self.disband(sender=self.manager)
        self.claim_liquidity(sender=self.b, position_id=0)
