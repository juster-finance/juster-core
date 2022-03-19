from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class CreateEventTestCase(PoolBaseTestCase):
    def test_should_fail_if_free_liquidity_is_less_than_next_event_liquidity(self):
        self.add_line(max_active_events=10)
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()

        for event_id in range(9):
            self.create_event(event_line_id=0)
            self.wait(3600)

        self.assertEqual(self.get_next_liquidity(), 10)

        self.add_line(max_active_events=10)
        self.assertEqual(self.get_next_liquidity(), 5)

        for event_id in range(2):
            self.create_event(event_line_id=1)
            self.wait(3600)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(event_line_id=1)

        err_text = 'Not enough liquidity to run event'
        self.assertTrue(err_text in str(cm.exception))


    def test_should_fail_if_zero_events_in_line_added(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.add_line(max_active_events=0)
        err_text = 'Line should have at least one event'
        self.assertTrue(err_text in str(cm.exception))

