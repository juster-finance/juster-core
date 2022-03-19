from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class SetEntryLockPeriodTestCase(PoolBaseTestCase):
    def test_should_change_entry_lock_period_if_manager_calls(self):
        self.set_entry_lock_period(new_period=3600, sender=self.manager)
        self.assertEqual(self.storage['entryLockPeriod'], 3600)

        self.set_entry_lock_period(new_period=0, sender=self.manager)
        self.assertEqual(self.storage['entryLockPeriod'], 0)


    def test_should_fail_to_set_new_entry_lock_period_if_not_manager(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.set_entry_lock_period(new_period=3600, sender=self.c)
        self.assertTrue('Not a contract manager' in str(cm.exception))

