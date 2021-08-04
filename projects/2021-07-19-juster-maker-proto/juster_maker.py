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

from config import (
    SHELL_URI,
    JUSTER_ADDRESS,
    KEY,
    TRANSACTIONS_QUEUE_SIZE,
    CREATORS,
    EVENT_LINES_PARAMS_FN
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

    def __init__(self):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info('juster maker initialized')
        self.clients = [
            pytezos.using(key=KEY, shell=SHELL_URI)
            # TODO: multiple clients support with multiple KEYs provided
        ]

        self.contract = self.clients[0].contract(JUSTER_ADDRESS)
        self.event_lines = EventLines.load(EVENT_LINES_PARAMS_FN)
        self.dd_client = JusterDipDupClient()
        self.operations_queue = Queue(TRANSACTIONS_QUEUE_SIZE)


    def create_executors(self):

        # for each event line one EventCreationEmitter is created:
        event_creation_executors = [
            EventCreationEmitter(
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client,
                event_params=params,
            )
            for params in self.event_lines.get()
        ]

        # for each event line one LineLiquidityProvider is created:
        line_liquidity_executors = [
            LineLiquidityProvider(
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client,
                event_params=params,
            )
            for params in self.event_lines.get()
        ]

        # for each client key one BulkSender is created:
        bulk_senders = [
            BulkSender(
                client=client,
                operations_queue=self.operations_queue)
            for client in self.clients
        ]

        # one WithdrawCaller, ForceMajeureCaller and CanceledCaller created:
        support_callers = [
            WithdrawCaller(
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client),

            ForceMajeureCaller(
                contract=self.contract,
                operations_queue=self.operations_queue,
                dd_client=self.dd_client),

            CanceledCaller(
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

