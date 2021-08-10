from unittest import TestCase
from unittest.mock import patch, Mock
import asyncio
from asyncio import Queue

import tests.config as config
from executors import BulkSender


@patch('pytezos.PyTezosClient')
class BulkSenderTest(TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.operations_queue = Queue(10)


    def test_transaction_is_send(self, client):

        bs = BulkSender(
            config=config,
            client=client,
            operations_queue=self.operations_queue
        )

        self.loop.run_until_complete(
            self.operations_queue.put('some transaction'))

        self.assertEqual(self.operations_queue.qsize(), 1)
        self.loop.run_until_complete(bs.execute())
        client.bulk.assert_called()
        self.assertEqual(self.operations_queue.qsize(), 0)


    def test_failed_transaction_returned_to_the_queue(self, client):

        bs = BulkSender(
            config=config,
            client=client,
            operations_queue=self.operations_queue
        )

        self.loop.run_until_complete(
            self.operations_queue.put('some transaction'))

        client.bulk = Mock(
            side_effect=Exception('TODO: change me to RPC error'))

        self.assertEqual(self.operations_queue.qsize(), 1)
        self.loop.run_until_complete(bs.execute())
        client.bulk.assert_called()
        self.assertEqual(self.operations_queue.qsize(), 1)


    ''' TODO:
    def test_failed_transaction_runned_again(self):
        pass
    '''

