from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class TriggerPauseDepositTestCase(PoolBaseTestCase):
    def test_should_fail_if_not_manager_calls_pause(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_pause_deposit(sender=self.c)

        self.assertTrue('Not a contract manager' in str(cm.exception))

    def test_should_fail_to_deposit_liquidity_when_it_paused(self):
        self.add_line(sender=self.manager)
        entry_id = self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id=entry_id)
        self.trigger_pause_deposit(sender=self.manager)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.deposit_liquidity(amount=1)

        self.assertTrue('Deposit is paused' in str(cm.exception))

    def test_should_succeed_to_approve_liquidity_when_it_paused(self):
        self.add_line(sender=self.manager)
        entry_id = self.deposit_liquidity(amount=1000)
        self.trigger_pause_deposit(sender=self.manager)
        self.approve_liquidity(entry_id=entry_id)

    def test_should_accept_liquidity_when_unpaused(self):
        self.add_line(sender=self.manager)

        self.trigger_pause_deposit(sender=self.manager)
        self.trigger_pause_deposit(sender=self.manager)

        entry_id = self.deposit_liquidity(amount=1000)
        self.trigger_pause_deposit(sender=self.manager)
