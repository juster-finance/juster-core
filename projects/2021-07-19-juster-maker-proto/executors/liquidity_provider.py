from executors import EventCreationEmitter
import asyncio
import time
from config import LIQUIDITY_MAX_SLIPPAGE, PROVIDE_LIQUIDITY_AMOUNT


class LineLiquidityProvider(EventCreationEmitter):
    """ Listens to the dipdup for curated events and provides liquidity
        For each event line one LineLiquidityProvider should be runned
        Liquidity Provider is very similar to EventCreationEmitter, this is why
        they share some code
    """

    async def _make_provide_liquidity_transaction(self, event_id, amount, a, b):

        provide_params = {
            'eventId': event_id,
            'expectedRatioAboveEq': a,
            'expectedRatioBelow': b,
            'maxSlippage': LIQUIDITY_MAX_SLIPPAGE
        }

        op = self.contract.provideLiquidity(provide_params).with_amount(amount)
        transaction = op.as_transaction()
        await self.operations_queue.put(transaction)

        self.logger.info(
            f'provided liquidity to {event_id=}, {a=}, {b=}, {amount=}')


    async def provide_liquidity(self):

        # getting info about last event in line:
        last_event = self.get_last_event_info()

        # checking that event is still opened:
        if last_event['bets_close_time'].timestamp() < time.time():
            self.logger.info(
                f'LineLiquidityProvider: betting is finished, skipping')
            return

        pools_value = last_event['pool_above_eq'] + last_event['pool_below']
        minimal_value = 1e-6
        if pools_value < minimal_value:
            # TODO: evaluate a/b
            event_id = last_event['id']
            amount = PROVIDE_LIQUIDITY_AMOUNT
            a = 1
            b = 1

            await self._make_provide_liquidity_transaction(
                event_id, amount, a, b)
            # making transaction to fill pool:

            # It is very possible that time from transaction creation to signing
            # and bulking exceed 120 seconds that setted in period. Because of
            # this it is required to block this provide_liquidity for some time.
            # The easiest working way: make it sleep 10 mins

            # TODO: is it possible to await for some dipdup subscription call?
            await asyncio.sleep(600)


    async def execute(self):
        # TODO: do I need here repeat_until_succeed?
        return await self.provide_liquidity()

