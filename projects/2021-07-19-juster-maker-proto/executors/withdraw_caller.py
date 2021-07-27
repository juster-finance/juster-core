import logging
from executors.loop_executor import LoopExecutor
import time
import asyncio
from utility import timestamp_to_date
from pytezos.michelson.micheline import MichelsonRuntimeError


class WithdrawCaller(LoopExecutor):

    REWARD_SPLIT_FEE_AFTER = 24*60*60


    def __init__(self, period, contract, operations_queue, dd_client):
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
        self.logger = logging.getLogger(__name__)
        self.dd_client = dd_client


    async def _make_withdraw_transaction(self, event_id, address):

        withdrawing_params = {
            'eventId': event_id,
            'participantAddress': address
        }

        transaction = self.contract.withdraw(withdrawing_params).as_transaction()
        # testing that transaction would succeed:
        # TODO: is this temporal solution? or maybe I should move it into separate method?
        # if int(event_id) == 785:
        #     import pdb; pdb.set_trace()
        try:
            # self.contract.withdraw(withdrawing_params).interpret(
            #     storage=self.contract.storage())
            self.contract.storage['events'][event_id]()
        # except MichelsonRuntimeError as e:
        except KeyError as e:
            # assert 'Event is not found' in str(e)
            self.logger.error(f'Catched error in transaction emulation test:')
            self.logger.error(f'Event ID: {event_id}')
            self.logger.error(f'Address: {address}')
            self.logger.error(f'WARNING: ignoring this transaction')
            return

        await self.operations_queue.put(transaction)

        self.logger.info(f'added withdraw transaction with params: {withdrawing_params}')


    async def emmit_withdraw_transactions(self):

        # Calculating threshold closed date that activates reward split fee:
        closed_before = timestamp_to_date(time.time() - self.REWARD_SPLIT_FEE_AFTER)

        # Requesting events:
        withdrawable_events = self.dd_client.query_withdrawable_events(closed_before)

        for event in withdrawable_events:
            for position in event['positions']:
                address = position['user']['address']
                await self._make_withdraw_transaction(event['id'], address)

        # Waiting while all emitted transactions executed and dipdup updates:
        # TODO: it can took a lot of time, it is better to have some callback
        # or have another way to understand when transactions are completed:

        await asyncio.sleep(600)


    async def execute(self):
        return await self.emmit_withdraw_transactions()

