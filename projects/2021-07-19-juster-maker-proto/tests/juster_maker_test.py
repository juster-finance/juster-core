import asyncio
from unittest import TestCase

from juster_maker import JusterMaker
from unittest.mock import patch, AsyncMock, Mock
import tests.config as config


class JusterMakerTest(TestCase):

    def test_should_run_executor(self):

        mock_executor = AsyncMock()
        maker = JusterMaker(executors=[mock_executor])
        asyncio.run(maker.run())
        mock_executor.run.assert_awaited_once()

