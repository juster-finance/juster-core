from executors.loop_executor import LoopExecutor
import asyncio
import time


class LineLiquidityProvider(LoopExecutor):
    """ Listens to the dipdup for curated events and provides liquidity
        For each event line one LineLiquidityProvider should be runned
    """

    def __init__(self, period, contract, operations_queue, event_params, dd_client, creators):
        """ ...
            - contract: is pytezos object with Juster contract loaded and
                some key provided
            - event_params: params of the event
                - currency_pair: 
                - target_dynamics: should be float 1.0 - no dynamics
                - measure_period: in seconds
                - liquidity_percent: should be float, 0.01 is one percent
        """

        super().__init__(period)

        self.contract = contract
        self.operations_queue = operations_queue
        self.event_params = event_params
        self.dd_client = dd_client
        self.creators = creators


    async def _make_provide_liquidity_transaction(self, event_id, amount, a, b):

        provide_params = {
            'eventId': event_id,
            'expectedRatioAboveEq': a,
            'expectedRatioBelow': b,
            # TODO: set slippage 10%
            'maxSlippage': 1_000_000
        }

        transaction = self.contract.provideLiquidity(provide_params).with_amount(amount).as_transaction()
        await self.operations_queue.put(transaction)

        # TODO: make logging instead of prints:
        print(f'provided liquidity to {event_id=}, {a=}, {b=}, {amount=}')


    async def provide_liquidity(self):

        # getting info about last event in line:
        last_event = self.dd_client.query_last_line_event(
            self.event_params['currency_pair'],
            self.event_params['target_dynamics'],
            self.event_params['measure_period'],
            self.creators
        )

        # checking that event is still opened:
        if last_event['bets_close_time'].timestamp() < time.time():
            # TODO: again logging with name setup:
            print(f'LineLiquidityProvider: betting is finished, skipping')
            return

        pools_value = last_event['pool_above_eq'] + last_event['pool_below']
        minimal_value = 1e-6
        if pools_value < minimal_value:
            # TODO: evaluate a/b
            event_id = last_event['id']
            amount = 1_000_000
            a = 1
            b = 1

            await self._make_provide_liquidity_transaction(event_id, amount, a, b)
            # making transaction to fill pool:

            # wait untill this transaction is succeed (check each 30 secs last_event and that it updated)
            # -- or maybe check that juster_deposit emitted?

            # It is very possible that time from transaction creation to signing and bulking
            # exceed 120 seconds that setted in period. Because of this it is required to block
            # this provide_liquidity for some time. The easiest working way: make it sleep 10 mins

            # TODO: But I don't like this sleep, maybe there are better way to hold while transaction
            # is prepared?
            await asyncio.sleep(600)


    async def execute(self):
        # TODO: do I need here repeat_until_succeed?
        return await self.provide_liquidity()

