""" CLI tool that running Juster Maker """


from pytezos import pytezos
import asyncio
from asyncio import Queue
import time


from executors import (
    BulkSender,
    EventCreationEmitter,
    LineLiquidityProvider
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

        self.clients = [
            pytezos.using(key=KEY, shell=SHELL_URI)
            # TODO: multiple clients support with multiple KEYs provided
        ]

        self.contract = self.clients[0].contract(JUSTER_ADDRESS)
        self.event_lines = EventLines.load(EVENT_LINES_PARAMS_FN)
        self.dd_client = JusterDipDupClient()
        self.operations_queue = Queue(TRANSACTIONS_QUEUE_SIZE)

        self.event_lines.update_timestamps(self.dd_client)


    def create_executors(self):

        # for each event_params EventCreationEmitter is created:
        event_creation_executors = [
            EventCreationEmitter(
                period=20,
                contract=self.contract,
                operations_queue=self.operations_queue,
                event_params=params,
                next_at=params['next_at']
                # TODO: maybe instead of transfering next_at, transfer dd_client
                # and find last event params using dd_client inside EventCreationEmitter
                # constructor?
                
                ### TODO: maybe use dd_client in EventEmitter too?
            )
            for params in self.event_lines.get()
        ]

        line_liquidity_executors = [
            LineLiquidityProvider(
                period=120,
                contract=self.contract,
                operations_queue=self.operations_queue,
                event_params=params,
                dd_client=self.dd_client,
                creators=CREATORS
            )
            for params in self.event_lines.get()
        ]

        bulk_senders = [
            BulkSender(
                period=60,
                client=client,
                operations_queue=self.operations_queue)
            for client in self.clients
        ]

        self.executors = [
            *event_creation_executors,
            *line_liquidity_executors,
            *bulk_senders
        ]


    async def run(self):
        tasks = [executor.run() for executor in self.executors]
        await asyncio.gather(*tasks)


    def stop(self):
        for executor in self.executors:
            executor.stop()


def generate_event_lines():
    """ Recreating event_lines.json if this is required """

    event_lines = EventLines()
    event_lines.generate_new()
    event_lines.save(EVENT_LINES_PARAMS_FN)


async def run_maker():
    print(f'running maker:')
    maker = JusterMaker()
    maker.create_executors()
    await maker.run()


if __name__ == '__main__':
    asyncio.run(run_maker())
