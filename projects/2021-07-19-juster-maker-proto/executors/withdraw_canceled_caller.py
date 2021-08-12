from executors import WithdrawFinishedCaller
import time
import asyncio
from utility import timestamp_to_date
from pytezos.michelson.micheline import MichelsonRuntimeError


class WithdrawCanceledCaller(WithdrawFinishedCaller):


    async def query_canceled_to_withdraw(self):
        """ Requests list of events that have unwithdrawn positions and
            where status is CANCELED (force majeure)
        """

        return await self.dd_client.make_query('canceled_to_withdraw')


    async def emmit_cancel_withdraw_transactions(self):

        # Requesting events:
        events = await self.query_canceled_to_withdraw()

        self.logger.info(
            f'updated canceled to withdraw events list, {len(events)}')

        await self._make_transaction_for_events(events)
        # TODO: dipdup subscription?
        await asyncio.sleep(600)


    async def execute(self):
        return await self.emmit_cancel_withdraw_transactions()

