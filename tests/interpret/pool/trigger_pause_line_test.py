from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class TriggerPauseLineTestCase(PoolBaseTestCase):

    def test_should_decrease_active_events_on_pause(self):
        self.add_line(sender=self.manager, max_events=10)
        line_id = self.add_line(sender=self.manager, max_events=10)
        self.assertEqual(self.storage['maxEvents'], 20)
        self.trigger_pause_line(line_id=0, sender=self.manager)
        self.assertEqual(self.storage['maxEvents'], 10)

    def test_should_not_allow_to_trigger_pause_for_not_manager(self):
        self.add_line(sender=self.manager)
        line_id = self.add_line(sender=self.manager)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_pause_line(line_id=line_id, sender=self.c)
        self.assertTrue('Not a contract manager' in str(cm.exception))

    def test_should_increase_next_event_liquidity_on_pause(self):
        line_id = self.add_line(sender=self.manager, max_events=10)
        self.add_line(sender=self.manager, max_events=10)
        entry_id = self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id = entry_id)

        liquidity_before = self.get_next_liquidity()
        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        liquidity_after = self.get_next_liquidity()

        self.assertTrue(self.storage['lines'][line_id]['isPaused'])
        self.assertTrue(liquidity_after > liquidity_before)

    def test_double_trigger_pause_should_not_change_state(self):
        self.add_line(sender=self.manager, max_events=10)
        line_id = self.add_line(sender=self.manager, max_events=2)
        entry_id = self.deposit_liquidity(amount=1200)
        self.approve_liquidity(entry_id = entry_id)

        liquidity_before = self.get_next_liquidity()
        events_before = self.storage['maxEvents']

        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        self.trigger_pause_line(line_id=line_id, sender=self.manager)

        liquidity_after = self.get_next_liquidity()
        events_after = self.storage['maxEvents']

        self.assertEqual(liquidity_before, liquidity_after)
        self.assertEqual(events_before, events_after)

    def test_update_line_should_not_change_next_event_liquidity(self):

        # adding line:
        line_id = self.add_line(sender=self.manager, max_events=10)
        entry_id = self.deposit_liquidity(amount=100)
        self.approve_liquidity(entry_id = entry_id)
        next_event_liquidity_before = self.get_next_liquidity()

        # updating line:
        new_line_id = self.add_line(sender=self.manager, max_events=10)
        self.trigger_pause_line(line_id=line_id, sender=self.manager)

        self.assertEqual(
            next_event_liquidity_before,
            self.get_next_liquidity()
        )

    def test_should_fail_if_try_to_run_paused_line(self):
        self.add_line(sender=self.manager, max_events=10)
        line_id = self.add_line(sender=self.manager, max_events=10)
        entry_id = self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id = entry_id)
        self.trigger_pause_line(line_id=line_id, sender=self.manager)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(line_id=line_id)
        self.assertTrue('Line is paused' in str(cm.exception))

        # test that line can be runned if triggered pause again:
        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        self.create_event(line_id=line_id)

    def test_add_line_while_all_events_are_run_and_claim(self):
        line_one = self.add_line(sender=self.manager, max_events=1)
        line_two = self.add_line(sender=self.manager, max_events=1)

        entry_id = self.deposit_liquidity(amount=30, sender=self.a)
        self.approve_liquidity(entry_id=entry_id)

        self.create_event(line_id=line_one)
        self.wait(3600)
        self.create_event(line_id=line_two)

        # the case with increased max events:
        line_three = self.add_line(sender=self.manager, max_events=1)
        self.claim_liquidity(sender=self.a, shares=15)

        # the case with decreased max events:
        self.trigger_pause_line(line_id=line_two, sender=self.manager)
        self.trigger_pause_line(line_id=line_three, sender=self.manager)
        self.claim_liquidity(sender=self.a, shares=15)

