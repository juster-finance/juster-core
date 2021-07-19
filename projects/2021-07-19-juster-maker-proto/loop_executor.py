import asyncio
from abc import abstractmethod


class LoopExecutor:
    """ Executes self.execute each period seconds """

    def __init__(self, period):
        self.period = period
        self.loop = asyncio.get_event_loop()


    def run(self):
        self.task = self.loop.create_task(self.loop_task())


    @abstractmethod
    async def execute(self):
        raise NotImplemented('method execute should be implemented')


    async def loop_task(self):
        while True:
            await self.execute()
            await asyncio.sleep(self.period)


    def stop(self):
        self.task.cancel()

