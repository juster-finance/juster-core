import asyncio
from unittest import TestCase
from event_emitter import EventCreationEmitter
from bulk_sender import BulkSender
from unittest.mock import MagicMock, Mock, patch
from asyncio import Queue


DEFAULT_EVENT_PARAMS = params = {
    'currency_pair': 'XTZ-USD',
    # 'first_at': 
    'target_dynamics': 1_000_000,
    'bets_period': 900,
    'measure_period': 900,
    'liquidity_percent': 10_000,
    'expiration_fee': 100_000,
    'measure_start_fee': 100_000
}


class EventEmitterTest(TestCase):

    @patch('pytezos.ContractInterface')
    def test_event_is_created(self, contract):
        loop = asyncio.get_event_loop()
        operations_queue = Queue(10)
        event_emitter = EventCreationEmitter(
            period=1,
            contract=contract,
            operations_queue=operations_queue,
            event_params=DEFAULT_EVENT_PARAMS)

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

        bs = BulkSender(period=1, client=client, operations_queue=self.operations_queue)
        self.loop.run_until_complete(self.operations_queue.put('some transaction'))
        self.assertEqual(self.operations_queue.qsize(), 1)
        self.loop.run_until_complete(bs.execute())
        client.bulk.assert_called()
        self.assertEqual(self.operations_queue.qsize(), 0)


    @patch('pytezos.PyTezosClient')
    def test_failed_transaction_returned_to_the_queue(self, client):

        bs = BulkSender(period=1, client=client, operations_queue=self.operations_queue)
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
