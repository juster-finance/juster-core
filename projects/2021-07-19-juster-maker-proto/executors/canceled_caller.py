import logging
from executors.loop_executor import LoopExecutor
import time
import asyncio
from utility import timestamp_to_date
from pytezos.michelson.micheline import MichelsonRuntimeError


# TODO: this caller code is very similar to WithdrawCaller, should I use
# some intermediate class that shared code? or keep it simple?

class CanceledCaller(LoopExecutor):


    def __init__(self, period, contract, operations_queue, dd_client):
        """ ...
            - contract: is pytezos object with Juster contract loaded and
                some key provided
            - operations_queue: TODO:
            - dd_client: TODO:
        """

        # TODO: starts_from = 'datetime unixtime', every=seconds instead of period
        # TODO: rename period to update_period
        super().__init__(period)

        self.contract = contract
        self.operations_queue = operations_queue
        self.logger = logging.getLogger(__name__)
        self.dd_client = dd_client


    async def _make_cancel_withdraw_transaction(self, event_id, address):

        withdrawing_params = {
            'eventId': event_id,
            'participantAddress': address
        }

        transaction = self.contract.withdraw(withdrawing_params).as_transaction()
        # testing that transaction would succeed:
        # TODO: is this temporal solution? or maybe I should move it into separate method?
        try:
            self.contract.storage['events'][event_id]()
        except KeyError as e:
            self.logger.error(f'Catched error in transaction emulation test (CANCELED WITHDRAW):')
            self.logger.error(f'Event ID: {event_id}')
            self.logger.error(f'Address: {address}')
            self.logger.error(f'WARNING: ignoring this transaction')
            return

        await self.operations_queue.put(transaction)

        self.logger.info(f'added canceled withdraw transaction with params: {withdrawing_params}')


    async def emmit_cancel_withdraw_transactions(self):

        # Requesting events:
        withdrawable_events = self.dd_client.query_canceled_to_withdraw()

        if len(withdrawable_events):
            self.logger.info(f'updated canceled to withdraw events list, {len(withdrawable_events)}')

            for event in withdrawable_events:
                for position in event['positions']:
                    address = position['user']['address']
                    await self._make_cancel_withdraw_transaction(event['id'], address)

            # Waiting while all emitted transactions executed and dipdup updates:
            # TODO: it can took a lot of time, it is better to have some callback
            # or have another way to understand when transactions are completed:

            await asyncio.sleep(600)


    async def execute(self):
        return await self.emmit_cancel_withdraw_transactions()

