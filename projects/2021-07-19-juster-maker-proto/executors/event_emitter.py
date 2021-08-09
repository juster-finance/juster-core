from executors import EventLoopExecutor
import time
from utility import make_next_hour_timestamp


# TODO: rename to EventCreationCaller
class EventCreationEmitter(EventLoopExecutor):

    def __init__(
            self,
            config,
            contract,
            operations_queue,
            dd_client,
            event_params
        ):
        """ Creates new EventCreationCaller,
        - contract: juster contract, pytezos instance
        - operations_queue: queue object where transactions should go
        - dd_client: JusterDipDupClient instance
        - period: time in seconds used to sleep before executor re runned
        - event_params: params of the event
            - currency_pair: string with currency used in event
            - target_dynamics: should be float 1.0 - no dynamics
            - measure_period: in seconds
            - liquidity_percent: should be float, 0.01 is one percent
        """

        super().__init__(config, contract, operations_queue, dd_client)

        self._verify_event_params(event_params)
        self.event_params = event_params
        self.next_at = None


    async def get_last_event_info(self):
        """ Returns actual data about last event in the line using dipdup query
            If there are no event with requested line params, returns None
        """

        last_events = await self.dd_client.make_query(
            query_name='last_line_event',
            currency_pair=self.event_params['currency_pair'],
            target_dynamics=self.event_params['target_dynamics'],
            measure_period=self.event_params['measure_period'],
            creators=self.config.CREATORS
        )

        if len(last_events):
            return last_events[0]


    async def get_next_close_timestamp(self):
        """ Requests last event close timestamp using DipDupClient
            this timestamp used to schedule this event
        """

        last_event = await self.get_last_event_info()

        if last_event:
            last_bets_close = int(last_event['bets_close_time'].timestamp())
            # TODO: it is possible that dipdup data have not indexed emitted
            # events if it was called right after last event was created. Is
            # there is any solution?
            return last_bets_close

        else:
            hour_timestamp = make_next_hour_timestamp()
            self.logger.info(f'last bets close timestamp is not found: '
                  + f'{self.event_params}, using next hour'
                  + f'timestamp = {hour_timestamp}')
            return hour_timestamp


    def _verify_event_params(self, event_params):
        # TODO: make Exceptions
        assert event_params['target_dynamics'] < 3.0
        assert event_params['target_dynamics'] > 0.33
        assert event_params['liquidity_percent'] < 0.3
        assert event_params['liquidity_percent'] >= 0.0


    async def _make_event_transaction(self):

        prec = self.config.DYNAMICS_PRECISION
        target_dynamics = int(self.event_params['target_dynamics'] * prec)

        prec = self.config.LIQUIDITY_PRECISION
        liquidity_percent = int(self.event_params['liquidity_percent'] * prec)

        # creating event:
        event_params = {
            'currencyPair': self.event_params['currency_pair'],
            'targetDynamics': target_dynamics,
            'betsCloseTime': self.next_at + self.event_params['bets_period'],
            'measurePeriod': self.event_params['measure_period'],
            'liquidityPercent': liquidity_percent,
        }

        fees = (
            self.event_params['expiration_fee']
            + self.event_params['measure_start_fee']
        )

        operation = self.contract.newEvent(event_params).with_amount(fees)
        transaction = operation.as_transaction()
        await self.put_transaction(transaction)


    async def create_event(self):

        # Updating info about next event time
        if self.next_at is None:
            self.next_at = await self.get_next_close_timestamp()

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

        # anyway if it is late or if new event created,
        # changing next_at timestamp:
        self.next_at = self.next_at + self.event_params['bets_period']
        self.logger.info(f'next event at: {self.next_at}')


    async def execute(self):
        # TODO: how can I catch all type of errors and rerun this?
        # TODO: maybe add here repeat_until_succeed?
        return await self.create_event()

