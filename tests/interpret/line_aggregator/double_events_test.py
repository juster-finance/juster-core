from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class DoubleEventsTest(LineAggregatorBaseTestCase):
    def test_double_event_should_fail(self):

        # adding some liquidity so it will be possible to create events:
        self.deposit_liquidity(self.a, amount=3_000_000)

        # creating line with a lot of possible events and bets period 5 min:
        self.add_line(
            currency_pair='XTZ-USD',
            max_active_events=10,
            bets_period=60*5
        )

        # creating first event should succeed:
        self.create_event(event_line_id=0, next_event_id=0)

        # creating second event at the same time should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(event_line_id=0, next_event_id=1)
        msg = 'Event cannot be created until previous event betsCloseTime'
        self.assertTrue(msg in str(cm.exception))

        # trying with 5 min waiting:
        self.wait(5*60)
        self.create_event(event_line_id=0, next_event_id=1)

        self.assertEqual(len(self.storage['events']), 2)

