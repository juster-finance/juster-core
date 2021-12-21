from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class DoubleEventsTest(LineAggregatorBaseTestCase):
    def test_double_event_should_fail(self):

        PERIOD = 5*60

        # creating line with a lot of possible events and bets period 5 min:
        self.add_line(
            currency_pair='XTZ-USD',
            max_active_events=10,
            bets_period=PERIOD
        )

        # adding some liquidity so it will be possible to create events:
        self.deposit_liquidity(self.a, amount=3_000_000)
        self.approve_liquidity(self.a, entry_position_id=0)

        # creating first event should succeed:
        self.create_event(event_line_id=0, next_event_id=0)

        # waiting almost until lastBetsCloseTime:
        lastBetsCloseTime = self.storage['lines'][0]['lastBetsCloseTime']
        delta_before_bets_close = lastBetsCloseTime - self.current_time
        self.assertTrue(delta_before_bets_close > 0)
        self.assertTrue(delta_before_bets_close <= PERIOD)
        self.wait(delta_before_bets_close - 1)

        # creating second event at the same time should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(event_line_id=0, next_event_id=1)
        msg = 'Event cannot be created until previous event betsCloseTime'
        self.assertTrue(msg in str(cm.exception))

        # waiting to complete 5 minutes:
        self.wait(1)
        self.create_event(event_line_id=0, next_event_id=1)

        self.assertEqual(len(self.storage['events']), 2)

