from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class NoAmountIncludedTestCase(PoolBaseTestCase):

    def test_entrypoints_should_not_allow_to_send_any_xtz(self):
        calls = [
            lambda: self.add_line(sender=self.manager, amount=100),
            lambda: self.approve_liquidity(sender=self.manager, amount=100),
            lambda: self.cancel_liquidity(sender=self.manager, amount=100),
            lambda: self.claim_liquidity(sender=self.manager, amount=100),
            lambda: self.withdraw_liquidity(sender=self.manager, amount=100),
            lambda: self.create_event(sender=self.manager, amount=100),
            lambda: self.trigger_pause_line(sender=self.manager, amount=100),
            lambda: self.trigger_pause_deposit(sender=self.manager, amount=100),
            lambda: self.set_entry_lock_period(sender=self.manager, amount=100),
            lambda: self.propose_manager(sender=self.manager, amount=100),
            lambda: self.accept_ownership(sender=self.manager, amount=100),
            lambda: self.set_delegate(sender=self.manager, amount=100),
        ]

        for call in calls:
            with self.assertRaises(MichelsonRuntimeError) as cm:
                call()
            err_text = 'Including tez using this entrypoint call is not allowed'
            self.assertTrue(err_text in str(cm.exception))

