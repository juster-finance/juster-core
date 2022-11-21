from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class AddLineTestCase(PoolBaseTestCase):
    def test_should_allow_admin_to_add_new_lines(self):
        self.add_line(sender=self.manager)

    def test_should_fail_if_not_admin_adds_new_line(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.add_line(self.c)
        self.assertTrue('Not a contract manager' in str(cm.exception))

    def test_should_increase_max_events_if_not_paused(self):
        assert self.storage['maxEvents'] == 0
        self.add_line(sender=self.manager, max_events=17, is_paused=False)
        assert self.storage['maxEvents'] == 17

    def test_should_not_increase_max_events_if_paused(self):
        assert self.storage['maxEvents'] == 0
        line_id = self.add_line(
            sender=self.manager, max_events=42, is_paused=True
        )
        assert self.storage['maxEvents'] == 0
        self.trigger_pause_line(line_id=line_id, sender=self.manager)
        assert self.storage['maxEvents'] == 42

    def test_should_not_allow_add_zero_bet_period_line(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.add_line(sender=self.manager, bets_period=0)
        self.assertTrue(
            'betsPeriod should be more than 0' in str(cm.exception)
        )
