import asyncio
from unittest import TestCase
from executors import (
    EventCreationEmitter,
    BulkSender
)
from dipdup import JusterDipDupClient
from unittest.mock import MagicMock, Mock, patch
from asyncio import Queue
from datetime import datetime


# TODO: should it be easier to have separate object with default constructor?
DEFAULT_EVENT_PARAMS = params = {
    'currency_pair': 'XTZ-USD',
    'target_dynamics': 1.0,
    'bets_period': 900,
    'measure_period': 900,
    'liquidity_percent': 0.01,
    'expiration_fee': 100_000,
    'measure_start_fee': 100_000,
    'bets_close_time': datetime.now()
}


class EventEmitterTest(TestCase):

    @patch('pytezos.ContractInterface')
    def test_event_is_created(self, contract):
        loop = asyncio.get_event_loop()
        operations_queue = Queue(10)

        # patching dipdup to use prepared data instead of making real call:
        # return value from JusterDipDupClient.make_quert is the list
        # of the events:
        dd_response = [DEFAULT_EVENT_PARAMS.copy()]
        with patch.object(
                JusterDipDupClient,
                'make_query',
                return_value=dd_response) as mock_method:

            dd_client = JusterDipDupClient()
            # creating event_emitter using patched dipdup client and pytezos
            event_emitter = EventCreationEmitter(
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


class BulkSenderTest(TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.operations_queue = Queue(10)


    @patch('pytezos.PyTezosClient')
    def test_transaction_is_send(self, client):

        bs = BulkSender(client=client, operations_queue=self.operations_queue)
        self.loop.run_until_complete(self.operations_queue.put('some transaction'))
        self.assertEqual(self.operations_queue.qsize(), 1)
        self.loop.run_until_complete(bs.execute())
        client.bulk.assert_called()
        self.assertEqual(self.operations_queue.qsize(), 0)


    @patch('pytezos.PyTezosClient')
    def test_failed_transaction_returned_to_the_queue(self, client):

        bs = BulkSender(client=client, operations_queue=self.operations_queue)
        self.loop.run_until_complete(self.operations_queue.put('some transaction'))
        client.bulk = Mock(side_effect=Exception('TODO: change me to RPC error'))
        self.assertEqual(self.operations_queue.qsize(), 1)
        self.loop.run_until_complete(bs.execute())
        client.bulk.assert_called()
        self.assertEqual(self.operations_queue.qsize(), 1)


    ''' TODO:
    def test_failed_transaction_runned_again(self):
        pass
    '''

