from unittest import TestCase
from unittest.mock import patch
import asyncio
from asyncio import Queue

import tests.config as config
from executors import NewEventCaller
from dipdup import JusterDipDupClient
from tests.data import DEFAULT_EVENT_PARAMS


class NewEventCallerTest(TestCase):

    def setUp(self):
        # patching dipdup to use prepared data instead of making real call:
        # return value from JusterDipDupClient.make_quert is the list
        # of the events:
        self.dd_client_patcher = patch(
            'dipdup.JusterDipDupClient.make_query',
            return_value=[DEFAULT_EVENT_PARAMS.copy()])
        self.dd_client_patcher.start()


    @patch('pytezos.ContractInterface')
    def test_event_is_created(self, contract):
        loop = asyncio.get_event_loop()
        operations_queue = Queue(10)
        dd_client = JusterDipDupClient(config)

        event_emitter = NewEventCaller(
            config=config,
            contract=contract,
            operations_queue=operations_queue,
            event_params=DEFAULT_EVENT_PARAMS.copy(),
            dd_client=dd_client)

        loop.run_until_complete(event_emitter.execute())

        contract.newEvent.assert_called()
        self.assertEqual(operations_queue.qsize(), 1)

    # TODO: Test that event created after first_at
    # TODO: Test that event created with correct params
    # TODO: Test that second event is created after period time have passed

    def tearDown(self):
        self.dd_client_patcher.stop()

