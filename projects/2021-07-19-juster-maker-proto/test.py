import asyncio
from unittest import TestCase
from event_emitter import EventCreationEmitter
from bulk_sender import BulkSender
from unittest.mock import MagicMock
from unittest.mock import patch
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

    @patch('pytezos.PyTezosClient')
    def test_transaction_is_send(self, client):
        loop = asyncio.get_event_loop()
        operations_queue = Queue(10)
        bs = BulkSender(period=1, client=client, operations_queue=operations_queue)

        loop.run_until_complete(operations_queue.put('some transaction'))
        self.assertEqual(operations_queue.qsize(), 1)

        result = loop.run_until_complete(bs.execute())

        client.bulk.assert_called()
        self.assertEqual(operations_queue.qsize(), 0)

    ''' TODO:
    def test_failed_transaction_returned_to_the_queue(self):
        pass

    def test_failed_transaction_runned_again(self):
        pass
    '''
