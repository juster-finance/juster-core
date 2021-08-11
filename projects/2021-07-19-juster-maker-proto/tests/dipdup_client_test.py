import asyncio
from unittest import TestCase

from dipdup import JusterDipDupClient
from unittest.mock import Mock
import tests.config as config
from urllib.error import URLError
from http.client import RemoteDisconnected
from tests.data import DEFAULT_DIPDUP_EVENT_RESPONSE


class DipDupClientTest(TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()


    def test_should_make_multiple_attempts_with_URLError_and_then_fail(self):
        mock_endpoint = Mock(side_effect=URLError('TODO: add reason here'))
        dd_client = JusterDipDupClient(config)
        dd_client.endpoint = mock_endpoint

        with self.assertRaises(URLError) as cm:
            self.loop.run_until_complete(dd_client.make_query('all_events'))

        self.assertEqual(mock_endpoint.call_count, config.MAX_RETRY_ATTEMPTS)


    def test_should_retry_if_RemoteDisconnected_and_succeed(self):

        raise_three_errors_and_then_succeed = [
            RemoteDisconnected('TODO: add reason here'),
            RemoteDisconnected('TODO: add reason here'),
            RemoteDisconnected('TODO: add reason here'),
            DEFAULT_DIPDUP_EVENT_RESPONSE
        ]

        mock_endpoint = Mock(side_effect=raise_three_errors_and_then_succeed)
        dd_client = JusterDipDupClient(config)
        dd_client.endpoint = mock_endpoint

        self.loop.run_until_complete(dd_client.make_query('all_events'))
        self.assertEqual(mock_endpoint.call_count, 4)

