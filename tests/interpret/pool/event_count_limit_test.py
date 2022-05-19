from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class EventCountLimitCase(PoolBaseTestCase):
    def test_exceeding_event_count_should_fail(self):

        PERIOD = 5*60

        # creating line with a lot of possible events and bets period 5 min:
        self.add_line(
            currency_pair='XTZ-USD',
            max_events=3,
            bets_period=PERIOD
        )

        # adding some liquidity so it will be possible to create events:
        self.deposit_liquidity(self.a, amount=3_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        # creating first three events should succeed:
        self.create_event(line_id=0, next_event_id=0)
        self.wait(PERIOD)

        self.create_event(line_id=0, next_event_id=1)
        self.wait(PERIOD)

        self.create_event(line_id=0, next_event_id=2)
        self.wait(PERIOD)

        # creating fourth event should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(line_id=0, next_event_id=3)
        msg = 'Max active events limit reached'
        self.assertTrue(msg in str(cm.exception))

        # closing event and trying again:
        self.pay_reward(event_id=0)
        self.create_event(line_id=0, next_event_id=3)

        # the first event is not removed:
        self.assertEqual(len(self.storage['events']), 4)

