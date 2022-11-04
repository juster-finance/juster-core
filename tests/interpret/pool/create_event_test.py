from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class CreateEventTestCase(PoolBaseTestCase):
    def test_should_fail_if_free_liquidity_is_not_enough_to_start_next_event(
        self,
    ):
        self.add_line(max_events=10)
        self.deposit_liquidity(amount=100)
        self.approve_entry()

        for event_id in range(9):
            self.create_event(line_id=0)
            self.wait(3600)

        self.assertEqual(self.get_next_liquidity(), 10)

        self.add_line(max_events=10)
        self.assertEqual(self.get_next_liquidity(), 5)

        for event_id in range(2):
            self.create_event(line_id=1)
            self.wait(3600)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(line_id=1)

        err_text = 'Not enough liquidity to run event'
        self.assertTrue(err_text in str(cm.exception))

    def test_should_fail_if_zero_events_in_line_added(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.add_line(max_events=0)
        err_text = 'Line should have at least one event'
        self.assertTrue(err_text in str(cm.exception))

    def test_should_fail_if_next_event_id_is_already_was_an_event_before(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(amount=100)
        self.approve_entry()
        self.create_event(line_id=0, next_event_id=42)
        self.wait(3600)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(line_id=0, next_event_id=42)

        err_text = 'Event id is already taken'
        self.assertTrue(err_text in str(cm.exception))

    def test_should_reschedule_event_if_less_than_min_betting_time_left(self):
        line_id = self.add_line(
            max_events=2, bets_period=100, min_betting_period=40
        )
        self.deposit_liquidity(amount=100)
        self.approve_entry()

        # current time with 1 sec > than min_betting_period allows:
        self.current_time = 61
        event_id = self.create_event()
        self.assertEqual(
            self.storage['lines'][line_id]['lastBetsCloseTime'], 200
        )

        # current time with 85 secs expected betting period:
        self.current_time = 215
        event_id = self.create_event()
        self.assertEqual(
            self.storage['lines'][line_id]['lastBetsCloseTime'], 300
        )

    def test_should_allow_to_run_event_if_have_advance_time(self):
        line_id = self.add_line(max_events=2, bets_period=100, advance_time=10)
        self.deposit_liquidity(amount=100)
        self.approve_entry()

        # current time with 1 sec > than min_betting_period allows:
        self.current_time = 0
        event_id = self.create_event()
        self.assertEqual(
            self.storage['lines'][line_id]['lastBetsCloseTime'], 100
        )

        # too early to run event:
        self.current_time = 80
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event()
        err_text = 'Event cannot be created until previous event betsCloseTime'
        self.assertTrue(err_text in str(cm.exception))

        # good time:
        self.current_time = 91
        self.create_event()
        self.assertEqual(
            self.storage['lines'][line_id]['lastBetsCloseTime'], 200
        )
