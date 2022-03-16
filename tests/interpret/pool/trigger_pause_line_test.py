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

    def test_should_increase_next_event_liquidity_on_pause(self):
        line_id = self.add_line(sender=self.manager, max_active_events=10)
        self.add_line(sender=self.manager, max_active_events=10)
        entry_id = self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id = entry_id)

        liquidity_before = self.storage['nextEventLiquidity']
        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        liquidity_after = self.storage['nextEventLiquidity']

        self.assertTrue(self.storage['lines'][line_id]['isPaused'])
        self.assertTrue(liquidity_after > liquidity_before)

    def test_double_trigger_pause_should_not_change_state(self):
        self.add_line(sender=self.manager, max_active_events=10)
        line_id = self.add_line(sender=self.manager, max_active_events=2)
        entry_id = self.deposit_liquidity(amount=1200)
        self.approve_liquidity(entry_id = entry_id)

        liquidity_before = self.storage['nextEventLiquidity']
        events_before = self.storage['maxActiveEvents']

        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        self.trigger_pause_line(line_id=line_id, sender=self.manager)

        liquidity_after = self.storage['nextEventLiquidity']
        events_after = self.storage['maxActiveEvents']

        self.assertEqual(liquidity_before, liquidity_after)
        self.assertEqual(events_before, events_after)

    def test_update_line_should_not_change_next_event_liquidity(self):

        # adding line:
        line_id = self.add_line(sender=self.manager, max_active_events=10)
        entry_id = self.deposit_liquidity(amount=100)
        self.approve_liquidity(entry_id = entry_id)
        next_event_liquidity_before = self.storage['nextEventLiquidity']

        # updating line:
        new_line_id = self.add_line(sender=self.manager, max_active_events=10)
        self.trigger_pause_line(line_id=line_id, sender=self.manager)

        self.assertEqual(
            next_event_liquidity_before,
            self.storage['nextEventLiquidity']
        )

