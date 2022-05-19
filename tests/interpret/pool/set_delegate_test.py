from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class SetDelegateTestCase(PoolBaseTestCase):
    def test_should_change_delegator_if_manager_calls(self):
        self.set_delegate(sender=self.manager)

    def test_should_fail_to_change_delegator_if_not_manager_calls(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.set_delegate(sender=self.c)

        msg = 'Not a contract manager'
        self.assertTrue(msg in str(cm.exception))
