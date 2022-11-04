from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class EventCreateTimeshiftTestCase(PoolBaseTestCase):
    def test_should_be_possible_to_shift_lines_in_time(self):

        PERIOD = 5 * 60

        # creating line with two events and period 5 min that should be shifted
        # for 42 seconds:
        self.add_line(
            max_events=2, bets_period=PERIOD, last_bets_close_time=42
        )

        self.deposit_liquidity()
        self.approve_entry()

        self.create_event()
        shifted_time = self.storage['lines'][0]['lastBetsCloseTime'] % PERIOD
        self.assertEqual(shifted_time, 42)

        # making another event with late:
        self.wait(10_000)
        self.create_event()
        shifted_time = self.storage['lines'][0]['lastBetsCloseTime'] % PERIOD
        self.assertEqual(shifted_time, 42)
