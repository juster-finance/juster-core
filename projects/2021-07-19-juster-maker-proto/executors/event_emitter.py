import logging
from executors.loop_executor import LoopExecutor
import time
import asyncio


class EventCreationEmitter(LoopExecutor):

    DYNAMICS_PRECISION = 1_000_000
    LIQUIDITY_PRECISION = 1_000_000


    def __init__(self, period, contract, operations_queue, event_params, next_at):
        """ ...
            - contract: is pytezos object with Juster contract loaded and
                some key provided
            - event_params: params of the event
                - currency_pair: 
                - target_dynamics: should be float 1.0 - no dynamics
                - measure_period: in seconds
                - liquidity_percent: should be float, 0.01 is one percent
        """

        # TODO: starts_from = 'datetime unixtime', every=seconds instead of period
        # TODO: rename period to update_period
        super().__init__(period)

        self.contract = contract
        self.operations_queue = operations_queue
        self._verify_event_params(event_params)
        self.event_params = event_params
        self.next_at = next_at
        self.logger = logging.getLogger(__name__)


    def _verify_event_params(self, event_params):
        # TODO: make Exceptions
        assert event_params['target_dynamics'] < 3.0
        assert event_params['target_dynamics'] > 0.33
        assert event_params['liquidity_percent'] < 0.3
        assert event_params['liquidity_percent'] >= 0.0


    async def _make_event_transaction(self):

        # creating event:
        event_params = {
            'currencyPair': self.event_params['currency_pair'],
            'targetDynamics': int(self.event_params['target_dynamics'] * self.DYNAMICS_PRECISION),
            'betsCloseTime': self.next_at + self.event_params['bets_period'],
            'measurePeriod': self.event_params['measure_period'],
            'liquidityPercent': int(self.event_params['liquidity_percent'] * self.LIQUIDITY_PRECISION),
        }

        # TODO: should I move this fees from event_params into event emitter params?
        fees = self.event_params['expiration_fee'] + self.event_params['measure_start_fee']
        transaction = self.contract.newEvent(event_params).with_amount(fees).as_transaction()
        await self.operations_queue.put(transaction)

        self.logger.info(f'created newEvent transaction with parameters: {event_params}')


    async def create_event(self):

        # checking that this is time to create event:
        time_before_next = self.next_at - time.time()

        # skipping if need to wait more:
        if time_before_next > 0:
            return

        # there are a chance that event emitter runned late and it is better to
        # skip current event if more than a half of the bets_period elapsed:
        late_time = -time_before_next
        is_late = late_time > self.event_params['bets_period'] / 2

        if not is_late:
            await self._make_event_transaction()

        # anyway if it is late or if new event created, changing next_at timestamp:
        self.next_at = self.next_at + self.event_params['bets_period']
        self.logger.info(f'next event at: {self.next_at}')


    async def execute(self):
        # TODO: do I need here repeat_until_succeed?
        return await self.create_event()

