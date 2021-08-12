import logging
from pytezos import pytezos
import asyncio
from asyncio import Queue
import time


from executors import (
    BulkSender,
    NewEventCaller,
    ProvideLiquidityCaller,
    WithdrawFinishedCaller,
    ForceMajeureCaller,
    WithdrawCanceledCaller
)

from utility import (
    date_to_timestamp,
    timestamp_to_date,
    make_next_hour_timestamp
)

from event_lines import EventLines
from dipdup import JusterDipDupClient


# TODO: moving this to separate function looks very wrong. Need to think twice
# TODO: maybe it is better to make ConfigExecutorCreator or smth like this and
# split this func into separate methods?
# and maybe it can be combined with EventLines generator
def create_executors(
        config, clients, contract, operations_queue, dd_client, event_lines):
    """ Creates list of the Executor objects. One event creator and
        liquidity provider for each event line. One bulk sender for each
        client key. And one for each support callers.
    """

    event_creation_executors = [
        NewEventCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            dd_client=dd_client,
            event_params=params,
        )
        for params in event_lines.get()
    ]

    line_liquidity_executors = [
        ProvideLiquidityCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            dd_client=dd_client,
            event_params=params,
        )
        for params in event_lines.get()
    ]

    bulk_senders = [
        BulkSender(
            config=config,
            client=client,
            operations_queue=operations_queue)
        for client in clients
    ]

    support_callers = [
        WithdrawFinishedCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            dd_client=dd_client),

        ForceMajeureCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            dd_client=dd_client),

        WithdrawCanceledCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            dd_client=dd_client)
    ]

    executors = [
        *event_creation_executors,
        *line_liquidity_executors,
        *bulk_senders,
        *support_callers
    ]

    return executors


class JusterMaker:
    """
        Tool allowing to run events in cycle
        Orchestrated multiple loop executors
    """

    def __init__(self, executors):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.executors = executors
        self.logger.info('juster maker initialized')


    @classmethod
    def from_config(cls, config):
        """ Creates Juster Maker using only config attribute """

        clients = [
            pytezos.using(key=config.KEY, shell=config.SHELL_URI)
            # TODO: multiple clients support with multiple KEYs provided
        ]

        contract = clients[0].contract(config.JUSTER_ADDRESS)
        event_lines = EventLines.load(config.EVENT_LINES_PARAMS_FN)
        dd_client = JusterDipDupClient(config)
        operations_queue = Queue(config.TRANSACTIONS_QUEUE_SIZE)

        # TODO: something wrong here (just have this feeling):
        # maybe transfer config only and create all this vars inside
        # create_executors?
        executors = create_executors(
            config,
            clients,
            contract,
            operations_queue,
            dd_client,
            event_lines)

        return cls(executors=executors)


    async def run(self):
        tasks = [executor.run() for executor in self.executors]
        await asyncio.gather(*tasks)


    def stop(self):
        for executor in self.executors:
            executor.stop()

