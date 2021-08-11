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

    def __init__(
            self,
            config,
            clients,
            contract,
            event_lines,
            dd_client,
            executors):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.config = config
        self.clients = clients
        self.event_lines = event_lines
        self.dd_client = dd_client
        self.executors = executors

        operations_queue = Queue(config.TRANSACTIONS_QUEUE_SIZE)
        self.logger.info('juster maker initialized')


    @classmethod
    def from_config(cls, config):
        """ Creates Juster Maker using only config attribute """

        clients = [
            pytezos.using(key=config.KEY, shell=config.SHELL_URI)
            # TODO: multiple clients support with multiple KEYs provided
        ]

        contract = self.clients[0].contract(config.JUSTER_ADDRESS)
        event_lines = EventLines.load(config.EVENT_LINES_PARAMS_FN)
        dd_client = JusterDipDupClient(config)

        executors = self._create_executors()
        # TODO: should it create executors here?
        # -- one of the option is to transfer executors in attribute too

        return cls(
            config=config,
            clients=clients,
            contract=contract,
            event_lines=event_lines,
            dd_client=dd_client,
            executors=executors)


    def _create_executors(self):
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

