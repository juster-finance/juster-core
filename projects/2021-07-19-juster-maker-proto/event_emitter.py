from loop_executor import LoopExecutor
import time
from utility import repeat_until_succeed


class EventCreationEmitter(LoopExecutor):

    def __init__(self, period, contract, operations_queue, event_params):
        """ ...
            - contract: is pytezos object with Juster contract loaded and
                some key provided
        """

        # TODO: starts_from = 'datetime unixtime', every=seconds instead of period
        super().__init__(period)

        self.contract = contract
        self.operations_queue = operations_queue
        self.event_params = event_params

        self.currency_pair = event_params['currency_pair']


    async def create_event(self):
        event_params = {
            'currencyPair': self.event_params['currency_pair'],
            'targetDynamics': self.event_params['target_dynamics'],
            # TODO: using self.starts_from time in betsCloseTime so this time would
            # be more precise?
            'betsCloseTime': int(time.time()) + self.event_params['bets_period'],
            'measurePeriod': self.event_params['measure_period'],
            'liquidityPercent': self.event_params['liquidity_percent'],
        }

        fees = self.event_params['expiration_fee'] + self.event_params['measure_start_fee']
        transaction = self.contract.newEvent(event_params).with_amount(fees).as_transaction()
        await self.operations_queue.put(transaction)

        # TODO: make logging instead of prints:
        print(f'created newEvent transaction with parameters: {event_params}')


    async def execute(self):
        # TODO: do I need here repeat_until_succeed?
        return await self.create_event()

