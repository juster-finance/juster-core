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

