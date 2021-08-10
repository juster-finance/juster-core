import asyncio
from unittest import TestCase

from dipdup import JusterDipDupClient
from unittest.mock import MagicMock
import tests.config as config
from urllib.error import URLError


class DipDupClientTest(TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()


    def test_should_make_multiple_attempts_with_URLError(self):
        mock_endpoint = MagicMock(side_effect=URLError('TODO: add reason here'))
        dd_client = JusterDipDupClient(config)
        dd_client.endpoint = mock_endpoint

        with self.assertRaises(URLError) as cm:
            self.loop.run_until_complete(dd_client.make_query('all_events'))

        self.assertEqual(mock_endpoint.call_count, config.MAX_RETRY_ATTEMPTS)

