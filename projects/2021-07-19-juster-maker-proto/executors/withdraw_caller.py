from executors import EventLoopExecutor
import time
import asyncio
from utility import timestamp_to_date
from pytezos.michelson.micheline import MichelsonRuntimeError
from config import REWARD_SPLIT_FEE_AFTER


class WithdrawCaller(EventLoopExecutor):
    """ Executor that checks is there are any positions that can be withdrawn
        and if it is: prepares transaction to withdraw
        Works only with CLOSED events
    """

    async def _make_withdraw_transaction(self, event_id, address):
        """ Prepares withdraw transaction for event with given event_id and
            participant with given address """

        withdrawing_params = {
            'eventId': event_id,
            'participantAddress': address
        }

        operation = self.contract.withdraw(withdrawing_params)
        transaction = operation.as_transaction()

        # TODO: is this temporal solution?
        # There are some error with 7, 12 and 1708 events, where dipdup
        # have info about positions in this events and there no events in
        # contract (looks like force majeure issue)
        if not self.is_event_exist(event_id):
            return

        await self.put_transaction(transaction)


    async def _make_transaction_for_events(self, events):
        """ Creates withdraw transaction for each event in events """

        for event in events:
            for position in event['positions']:
                address = position['user']['address']
                await self._make_withdraw_transaction(event['id'], address)


    async def query_withdrawable_events(self, closed_before):
        """ Requests list of events that have unwithdrawn positions and
            where time after close > rewardFeeSplitAfter (24h by default)
        """

        return await self.dd_client.make_query(
            'withdrawable_events',
            closed_before=closed_before)


    async def emmit_withdraw_transactions(self):

        # Calculating threshold closed date that activates reward split fee:
        closed_before = timestamp_to_date(time.time() - REWARD_SPLIT_FEE_AFTER)

        # Requesting events:
        events = await self.query_withdrawable_events(closed_before)

        self.logger.info(f'updated withdrawable events list, {len(events)}')

        await self._make_transaction_for_events(events)

        # Waiting while all emitted transactions executed and dipdup updates:
        # TODO: it can took a lot of time, it is better to have some callback
        # or have another way to understand when transactions are completed:

        # TODO: is it possible to make dipdup subscription and await for it
        # to trigger instead of sleep?
        await asyncio.sleep(600)


    async def execute(self):
        return await self.emmit_withdraw_transactions()

