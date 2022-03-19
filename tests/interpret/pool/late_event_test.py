from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class LateEventTestCase(PoolBaseTestCase):
    def test_that_event_should_be_created_in_the_future_when_late(self):

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

        # creating first event:
        self.create_event(event_line_id=0, next_event_id=0)

        # waiting a lot more time than period:
        self.wait(PERIOD*10)

        # creating second event and checking that it is created in good time:
        self.create_event(event_line_id=0, next_event_id=1)
        lastBetsCloseTime = self.storage['lines'][0]['lastBetsCloseTime']
        delta_before_bets_close = lastBetsCloseTime - self.current_time
        self.assertTrue(delta_before_bets_close > 0)
        self.assertTrue(delta_before_bets_close <= PERIOD)

