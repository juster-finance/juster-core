import logging
from executors import WithdrawCaller
import time
import asyncio
from utility import timestamp_to_date
from pytezos.michelson.micheline import MichelsonRuntimeError


class CanceledCaller(WithdrawCaller):

    async def emmit_cancel_withdraw_transactions(self):

        # Requesting events:
        events = self.dd_client.query_canceled_to_withdraw()

        self.logger.info(
            f'updated canceled to withdraw events list, {len(events)}')

        await self._make_transaction_for_events(events)
        # TODO: dipdup subscription?
        await asyncio.sleep(600)


    async def execute(self):
        return await self.emmit_cancel_withdraw_transactions()

