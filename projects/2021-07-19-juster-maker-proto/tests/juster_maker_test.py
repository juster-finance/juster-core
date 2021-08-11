import asyncio
from unittest import TestCase

from juster_maker import JusterMaker
from unittest.mock import patch, AsyncMock
import tests.config as config


class JusterMakerTest(TestCase):

    @patch('executors.EventLoopExecutor', new_callable=AsyncMock)
    def test_should_run_executor(self, mock_executor):
        maker = JusterMaker(config)
        maker.executors = [mock_executor]
        asyncio.run(maker.run())

        mock_executor.run.assert_awaited_once()

