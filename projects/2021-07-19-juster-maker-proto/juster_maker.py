import logging
from pytezos import pytezos
import asyncio
from asyncio import Queue
import time


from executors import (
    BulkSender,
    EventCreationEmitter,
    LineLiquidityProvider,
    WithdrawCaller,
    ForceMajeureCaller,
    CanceledCaller
)

from utility import (
    date_to_timestamp,
    timestamp_to_date,
    make_next_hour_timestamp
)

from event_lines import EventLines
from dipdup import JusterDipDupClient


class JusterMaker:
    """
        Tool allowing to run events in cycle
        Orchestrated multiple loop executors
    """

    def __init__(self, config):

        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info('juster maker initialized')
        self.clients = [
            pytezos.using(key=config.KEY, shell=config.SHELL_URI)
            # TODO: multiple clients support with multiple KEYs provided
        ]

        self.contract = self.clients[0].contract(config.JUSTER_ADDRESS)
        self.event_lines = EventLines.load(config.EVENT_LINES_PARAMS_FN)
        self.dd_client = JusterDipDupClient(config)
        self.operations_queue = Queue(config.TRANSACTIONS_QUEUE_SIZE)


    def create_executors(self):
        """ Creates list of the LoopExecutor objects. One event creator and
            liquidity provider for each event line. One bulk sender for each
            client key. And one for each support callers.
        """

        event_creation_executors = [
            EventCreationEmitter(
                config=self.config,
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client,
                event_params=params,
            )
            for params in self.event_lines.get()
        ]

        line_liquidity_executors = [
            LineLiquidityProvider(
                config=self.config,
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client,
                event_params=params,
            )
            for params in self.event_lines.get()
        ]

        bulk_senders = [
            BulkSender(
                config=self.config,
                client=client,
                operations_queue=self.operations_queue)
            for client in self.clients
        ]

        support_callers = [
            WithdrawCaller(
                config=self.config,
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client),

            ForceMajeureCaller(
                config=self.config,
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client),

            CanceledCaller(
                config=self.config,
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client)
        ]

        self.executors = [
            *event_creation_executors,
            *line_liquidity_executors,
            *bulk_senders,
            *support_callers
        ]


    async def run(self):
        tasks = [executor.run() for executor in self.executors]
        await asyncio.gather(*tasks)


    def stop(self):
        for executor in self.executors:
            executor.stop()

