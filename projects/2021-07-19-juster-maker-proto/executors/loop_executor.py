""" Base class used to execute some method in the loop """
import logging
import asyncio
from abc import abstractmethod


class LoopExecutor:
    """ Executes self.execute each period seconds """

    def __init__(self, config):
        """ Creates new LoopExecutor
        - config: configuration object with EXECUTOR_UPDATE_PERIOD set up
        """

        self.config = config
        self.period = config.EXECUTOR_UPDATE_PERIOD
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f'created with period {self.period}')


    def run(self):
        self.task = self.loop.create_task(self.loop_task())
        return self.task


    @abstractmethod
    async def execute(self):
        raise NotImplemented('method execute should be implemented')


    async def loop_task(self):
        while True:
            await self.execute()
            await asyncio.sleep(self.period)


    def stop(self):
        self.task.cancel()

