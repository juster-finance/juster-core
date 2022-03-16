from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class TriggerPauseTestCase(PoolBaseTestCase):

    def test_should_not_allow_to_pause_last_line(self):
        self.add_line(sender=self.manager)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_pause_line(line_id=0, sender=self.manager)
        self.assertTrue('Need to have at least one line' in str(cm.exception))

    def test_should_decrease_active_events_on_pause(self):
        self.add_line(sender=self.manager, max_active_events=10)
        line_id = self.add_line(sender=self.manager, max_active_events=10)
        self.assertEqual(self.storage['maxActiveEvents'], 20)
        self.trigger_pause_line(line_id=0, sender=self.manager)
        self.assertEqual(self.storage['maxActiveEvents'], 10)

    def test_should_not_allow_to_trigger_pause_for_not_manager(self):
        self.add_line(sender=self.manager)
        line_id = self.add_line(sender=self.manager)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_pause_line(line_id=line_id, sender=self.c)
        self.assertTrue('Not a contract manager' in str(cm.exception))

