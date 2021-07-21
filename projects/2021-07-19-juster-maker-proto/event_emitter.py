from loop_executor import LoopExecutor
import time
from utility import repeat_until_succeed
import asyncio


class EventCreationEmitter(LoopExecutor):

    def __init__(self, period, contract, operations_queue, event_params, next_at):
        """ ...
            - contract: is pytezos object with Juster contract loaded and
                some key provided
        """

        # TODO: starts_from = 'datetime unixtime', every=seconds instead of period
        # TODO: rename period to update_period
        super().__init__(period)

        self.contract = contract
        self.operations_queue = operations_queue
        self.event_params = event_params
        self.currency_pair = event_params['currency_pair']
        self.next_at = next_at


    async def create_event(self):

        # checking that this is time to create event:
        time_before_next = self.next_at - time.time()

        if time_before_next > 0:
            print(f'time has not come, waiting a little: {time_before_next} secs')
            return

        # creating event:
        event_params = {
            'currencyPair': self.event_params['currency_pair'],
            'targetDynamics': self.event_params['target_dynamics'],
            'betsCloseTime': self.next_at + self.event_params['bets_period'],
            'measurePeriod': self.event_params['measure_period'],
            'liquidityPercent': self.event_params['liquidity_percent'],
        }

        # TODO: should I move this fees from event_params into event emitter params?
        fees = self.event_params['expiration_fee'] + self.event_params['measure_start_fee']
        transaction = self.contract.newEvent(event_params).with_amount(fees).as_transaction()
        await self.operations_queue.put(transaction)

        # TODO: make logging instead of prints:
        print(f'created newEvent transaction with parameters: {event_params}')

        # TODO: move bets_period somewhere into the self:
        self.next_at = self.next_at + self.event_params['bets_period']
        print(f'next event at: {self.next_at}')


    async def execute(self):
        # TODO: do I need here repeat_until_succeed?
        return await self.create_event()

